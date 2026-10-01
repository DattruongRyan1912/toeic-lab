"""Agent tools: the AI mentor can read and change almost every piece of learner data, audited and undoable."""
import json
from datetime import timedelta

import httpx

from server import config, models
from server.services import agent_tools, ai_agent_service
from server.utils import timeutil


def run(client, tool, **args):
    response = client.post("/api/ai/actions/execute", json={"tool": tool, "args": args, "source": "user"})
    assert response.status_code == 200, response.text
    return response.json()


def undo(client, result):
    response = client.post(f"/api/ai/actions/{result['action_id']}/undo")
    assert response.status_code == 200, response.text
    return response.json()


def test_registry_covers_learner_data_and_declarations_are_valid():
    names = set(agent_tools.REGISTRY)
    assert len(names) >= 25
    assert {
        "update_learner_profile", "remember_learner_fact", "create_flashcards_bulk", "reschedule_flashcard", "log_error_question",
        "update_error_log", "add_plan_item", "replan_week", "create_practice_questions", "add_lesson_note", "add_paraphrase_pair",
        "schedule_study_reminder", "set_roadmap_task", "get_skill_report", "get_study_plan",
    } <= names
    for decl in agent_tools.declarations():
        assert decl["name"] and decl["description"]
        if "parameters" in decl:
            assert decl["parameters"]["type"] == "object" and decl["parameters"]["properties"]
            assert set(decl["parameters"].get("required", [])) <= set(decl["parameters"]["properties"])


def test_profile_and_memory_tools_are_audited_and_undoable(client, seeded):
    exam = (timeutil.local_today() + timedelta(days=28)).isoformat()
    result = run(client, "update_learner_profile", target_score=850, exam_date=exam, study_days=["T2", "T4", "T6"], explanation_style="concise")
    assert result["undoable"] and set(result["data"]["changed"]) == {"target_score", "exam_date", "study_days", "explanation_style"}
    me = client.get("/api/users/me").json()
    assert (me["target_score"], me["study_days"], me["explanation_style"]) == (850, [0, 2, 4], "concise")
    assert client.get("/api/roadmaps").json()["total_weeks"] == 4
    undo(client, result)
    me = client.get("/api/users/me").json()
    assert (me["target_score"], me["exam_date"], me["study_days"]) == (800, None, [0, 1, 2, 3, 4, 5])
    assert client.get("/api/roadmaps").json()["total_weeks"] == 24
    assert client.post(f"/api/ai/actions/{result['action_id']}/undo").status_code == 409
    assert run(client, "update_learner_profile", target_score=800)["status"] == "noop"

    memory = run(client, "remember_learner_fact", content="Học viên chỉ rảnh 30 phút sau 21h", category="context")
    assert run(client, "remember_learner_fact", content="học viên chỉ rảnh 30 phút sau 21h")["status"] == "exists"
    forget = run(client, "forget_learner_fact", memory_id=memory["data"]["memory_id"])
    assert client.get("/api/learner/memories").json() == []
    undo(client, forget)
    assert [m["id"] for m in client.get("/api/learner/memories").json()] == [memory["data"]["memory_id"]]
    tools = [a["tool"] for a in client.get("/api/ai/actions").json()]
    assert tools[:3] == ["forget_learner_fact", "remember_learner_fact", "update_learner_profile"]


def test_vocabulary_and_srs_tools(client, seeded, db):
    bulk = run(client, "create_flashcards_bulk", cards=[
        {"word": "leverage", "meaning": "tận dụng", "example_sentence": "We leverage data."},
        {"word": "Postpone", "meaning": "hoãn", "example_sentence": "x"},
        {"word": "audit", "meaning": "kiểm toán", "example_sentence": "The audit starts on Monday."},
    ])
    assert bulk["data"]["created"] == ["leverage", "audit"] and bulk["data"]["skipped"][0]["word"] == "postpone"
    assert client.get("/api/flashcards/summary").json()["total_cards"] == 7

    edited = run(client, "update_flashcard", word="leverage", meaning="tận dụng (đòn bẩy)", ipa="/ˈlevərɪdʒ/")
    card = client.get("/api/flashcards?search=leverage").json()[0]
    assert (card["meaning"], card["ipa"]) == ("tận dụng (đòn bẩy)", "ˈlevərɪdʒ")
    undo(client, edited)
    card = client.get("/api/flashcards?search=leverage").json()[0]
    assert (card["meaning"], card["ipa"]) == ("tận dụng", None)

    client.post("/api/flashcards/1/review", json={"rating": 3})  # card 1 now waits 2 days
    assert 1 not in [c["card_id"] for c in client.get("/api/flashcards/due").json()]
    due_now = run(client, "reschedule_flashcard", card_id=1, action="due_now")
    assert 1 in [c["card_id"] for c in client.get("/api/flashcards/due").json()]
    undo(client, due_now)
    assert 1 not in [c["card_id"] for c in client.get("/api/flashcards/due").json()]

    deleted = run(client, "delete_flashcard", card_id=1)
    assert client.get("/api/flashcards/summary").json()["total_cards"] == 6
    undo(client, deleted)
    db.expire_all()
    assert db.query(models.UserCardSRS).filter_by(card_id=1).one().state == "review"
    assert db.query(models.SRSReviewLog).filter_by(card_id=1).count() == 1  # history restored too
    undo(client, bulk)
    assert client.get("/api/flashcards/summary").json()["total_cards"] == 5


def test_error_log_plan_and_roadmap_tools(client, seeded):
    logged = run(client, "log_error_question", question_no=108, error_type="GRAMMAR", root_cause="Nhầm trạng từ", user_choice="(B) unanimous")
    log = client.get("/api/error-logs").json()[0]
    assert (log["correct_choice"], log["user_choice"], log["lesson_number"], log["review_stage"]) == ("D", "B", 1, 0)
    mastered = run(client, "update_error_log", error_id=log["id"], status="mastered")
    assert client.get("/api/dashboard/stats").json()["learning_gaps"] == []
    undo(client, mastered)
    assert client.get("/api/error-logs").json()[0]["status"] == "unresolved"
    assert client.get("/api/dashboard/stats").json()["learning_gaps"][0]["topic"] == "Bẫy Vị Trí Trạng Từ"
    undo(client, logged)
    assert client.get("/api/error-logs").json() == []

    today = timeutil.local_today()
    added = run(client, "add_plan_item", title="Đọc 2 email Part 7", plan_date=today.isoformat(), estimated_minutes=10)
    week = client.get("/api/plan/week").json()
    custom = next(i for i in week["days"][0]["items"] if i["id"] == added["data"]["item_id"])
    assert (custom["kind"], custom["source"], custom["status"]) == ("custom", "user", "pending")
    moved = run(client, "update_plan_item", item_id=custom["id"], plan_date=(today + timedelta(days=1)).isoformat(), status="done")
    assert next(i for i in client.get("/api/plan/week").json()["days"][1]["items"] if i["id"] == custom["id"])["status"] == "done"
    undo(client, moved)
    assert any(i["id"] == custom["id"] and i["status"] == "pending" for i in client.get("/api/plan/week").json()["days"][0]["items"])

    before = {i["id"] for d in client.get("/api/plan/week").json()["days"] for i in d["items"] if i["source"] == "planner"}
    replanned = run(client, "replan_week", reason="test")
    after = {i["id"] for d in client.get("/api/plan/week").json()["days"] for i in d["items"] if i["source"] == "planner"}
    assert before and after and before.isdisjoint(after)
    undo(client, replanned)
    assert {i["id"] for d in client.get("/api/plan/week").json()["days"] for i in d["items"] if i["source"] == "planner"} == before
    undo(client, added)

    task = next(t for t in client.get("/api/roadmaps").json()["tasks"] if not t["is_completed"])
    done = run(client, "set_roadmap_task", task_id=task["id"], is_completed=True)
    assert client.get("/api/roadmaps").json()["progress_percent"] == 67
    undo(client, done)
    moved_start = run(client, "update_roadmap", start_date=(today - timedelta(days=15)).isoformat())
    assert client.get("/api/roadmaps").json()["current_week"] == 3
    undo(client, moved_start)
    assert client.get("/api/roadmaps").json()["current_week"] == 1


def test_ai_practice_questions_join_the_personal_bank(client, seeded):
    result = run(client, "create_practice_questions", lesson_number=2, questions=[
        {"sentence": "___ the delay, the shipment arrived intact.", "choice_a": "Despite", "choice_b": "Although", "choice_c": "Because",
         "choice_d": "So that", "correct_choice": "A", "explanation": "Despite + cụm danh từ", "trap_tag": "Bẫy Liên Từ vs Giới Từ",
         "distractor_analysis": "Although/Because cần mệnh đề"},
        {"sentence": "The meeting was moved ___ the manager was traveling.", "choice_a": "because", "choice_b": "because of",
         "choice_c": "due to", "choice_d": "despite", "correct_choice": "a", "explanation": "because + mệnh đề"},
        {"sentence": "No blank here at all, sorry.", "choice_a": "a", "choice_b": "b", "choice_c": "c", "correct_choice": "A", "explanation": "x"},
    ])
    assert len(result["data"]["question_ids"]) == 2 and result["data"]["rejected"][0]["reason"] == "thiếu chỗ trống ___"
    questions = client.get("/api/tests/AI_PRACTICE/questions?lesson=2").json()
    assert len(questions) == 2 and all(q["source"] == "ai_mentor" and q["lesson_number"] == 2 for q in questions)
    assert questions[0]["trap_tag"] == "Bẫy Liên Từ vs Giới Từ" and questions[1]["correct_choice"] == "A"
    assert client.get("/api/knowledge/lessons/2").json()["stats"]["question_count"] == 3
    assert any(t["test_id"] == "AI_PRACTICE" and t["available_questions"] == 2 for t in client.get("/api/tests").json())

    answered = client.post("/api/practice/submit", json={"answers": [{"question_id": questions[0]["id"], "choice": "B"}]}).json()
    assert answered["errors_logged"] == 1
    log = client.get("/api/error-logs").json()[0]
    assert (log["test_id"], log["lesson_number"], log["topic"]) == ("AI_PRACTICE", 2, "Bẫy Liên Từ vs Giới Từ")

    undo(client, result)
    assert client.get("/api/tests/AI_PRACTICE/questions").status_code == 404
    assert client.get("/api/learner/insights").status_code == 200  # history of deleted questions still computes


def test_notes_paraphrases_and_reminders_tools(client, seeded):
    note = run(client, "add_lesson_note", lesson_number=1, content="Trạng từ chen giữa trợ động từ và V3")
    detail = client.get("/api/knowledge/lessons/1").json()
    assert detail["notes"][0]["content"].startswith("Trạng từ") and detail["notes"][0]["source"] == "user"
    undo(client, note)
    assert client.get("/api/knowledge/lessons/1").json()["notes"] == []

    assert run(client, "add_paraphrase_pair", word_in_text="Postpone", word_in_answer="DELAY")["status"] == "exists"
    pair = run(client, "add_paraphrase_pair", word_in_text="reimburse", word_in_answer="pay back", meaning="hoàn tiền")
    assert any(p["word_in_text"] == "reimburse" for p in client.get("/api/knowledge/paraphrases").json())
    undo(client, pair)

    created = run(client, "schedule_study_reminder", scheduled_time="06:30", message="Ôn 10 thẻ")
    rid = created["data"]["reminder_id"]
    paused = run(client, "update_reminder", reminder_id=rid, is_active=False)
    removed = run(client, "delete_reminder", reminder_id=rid)
    assert client.get("/api/reminders").json() == []
    undo(client, removed)
    assert client.get("/api/reminders").json()[0]["is_active"] is False
    undo(client, paused)
    assert client.get("/api/reminders").json()[0]["is_active"] is True
    undo(client, created)
    assert client.get("/api/reminders").json() == []

    bad = client.post("/api/ai/actions/execute", json={"tool": "schedule_study_reminder", "args": {"scheduled_time": "25:00", "message": "x"}})
    assert bad.status_code == 422 and "HH:MM" in bad.json()["detail"]
    assert client.post("/api/ai/actions/execute", json={"tool": "drop_database", "args": {}}).status_code == 404
    assert len(client.get("/api/ai/tools").json()) == len(agent_tools.REGISTRY)


def _gemini(parts):
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": parts}}]})


def test_llm_reads_skills_then_creates_targeted_content(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    client.post("/api/learner/memories", json={"content": "Thích ví dụ về cloud/DevOps", "category": "preference"})
    client.patch("/api/learner/profile", json={"explanation_style": "socratic"})
    client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[111], "choice": "C"}]})
    calls = []
    new_question = {"sentence": "___ the outage, the deployment finished on time.", "choice_a": "Despite", "choice_b": "Although",
                    "choice_c": "Because", "choice_d": "Unless", "correct_choice": "A", "explanation": "Despite + N",
                    "trap_tag": "Bẫy Liên Từ vs Giới Từ"}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            system = body["systemInstruction"]["parts"][0]["text"]
            assert "Thích ví dụ về cloud/DevOps" in system and "Gợi mở" in system and "Bài 02" in system
            return _gemini([{"functionCall": {"id": "c1", "name": "get_skill_report", "args": {}}}])
        if len(calls) == 2:
            report = body["contents"][-1]["parts"][0]["functionResponse"]["response"]["result"]
            weakest = report["data"]["lessons"][0]["lesson"]
            assert weakest == 2
            return _gemini([{"functionCall": {"id": "c2", "name": "create_practice_questions",
                                              "args": {"lesson_number": weakest, "questions": [new_question]}}}])
        result = body["contents"][-1]["parts"][0]["functionResponse"]["response"]["result"]
        assert result["status"] == "success" and result["undoable"]
        return _gemini([{"text": "Đã tạo 1 câu luyện Bài 02 cho bạn."}])

    monkeypatch.setattr(ai_agent_service, "_http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    data = client.post("/api/ai/chat", json={"message": "Tạo câu luyện cho điểm yếu nhất của tôi"}).json()
    assert data["reply"].startswith("Đã tạo") and [a["tool"] for a in data["actions_taken"]] == ["get_skill_report", "create_practice_questions"]
    read, write = data["actions_taken"]
    assert "data" not in read and write["undoable"] and write["action_id"]
    assert len(client.get("/api/tests/AI_PRACTICE/questions?lesson=2").json()) == 1
    undo(client, write)
    assert client.get("/api/tests/AI_PRACTICE/questions").status_code == 404


def test_offline_commands_still_change_data_through_tools(client, seeded):
    remembered = client.post("/api/ai/chat", json={"message": "Ghi nhớ: tôi hay sai bẫy liên từ khi vội"}).json()
    action = remembered["actions_taken"][0]
    assert remembered["provider"] == "offline" and action["tool"] == "remember_learner_fact" and action["undoable"]
    assert client.get("/api/learner/memories").json()[0]["content"] == "tôi hay sai bẫy liên từ khi vội"

    replanned = client.post("/api/ai/chat", json={"message": "Lập lại kế hoạch giúp tôi"}).json()
    assert replanned["actions_taken"][0]["tool"] == "replan_week"
    plan = client.post("/api/ai/chat", json={"message": "Kế hoạch hôm nay của tôi?"}).json()
    assert "Kế hoạch hôm nay" in plan["reply"] and plan["actions_taken"] == []

    sessions = client.get("/api/learner/insights").json()["study_minutes"][-1]["by_kind"]
    assert sessions.get("mentor") == 1.5  # 3 mentor questions x 30s


def test_every_read_tool_result_is_json_safe_for_the_llm(client, seeded, monkeypatch):
    """Regression: get_learner_overview returned datetimes and crashed /api/ai/chat with a 500."""
    monkeypatch.setattr(config, "DEEPSEEK_API_KEY", "ds-key")
    client.patch("/api/learner/profile", json={"exam_date": (timeutil.local_today() + timedelta(days=30)).isoformat()})
    read_tools = [s.name for s in agent_tools.REGISTRY.values() if not s.writes]
    args = {"get_lesson": {"lesson_number": 1}}
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["messages"][-1]["role"] == "tool":
            seen.append(json.loads(body["messages"][-1]["content"]))
        if len(seen) < len(read_tools):
            name = read_tools[len(seen)]
            call = {"id": f"t{len(seen)}", "type": "function", "function": {"name": name, "arguments": json.dumps(args.get(name, {}))}}
            return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [call]}}]})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "Xong"}}]})

    monkeypatch.setattr(ai_agent_service, "_http_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(ai_agent_service, "run_agent", _rounds(ai_agent_service.run_agent, len(read_tools) + 1))
    response = client.post("/api/ai/chat", json={"message": "Đọc hết dữ liệu của tôi"})
    assert response.status_code == 200, response.text
    assert [r["tool"] for r in seen] == read_tools and all(r["status"] == "success" for r in seen)
    overview = next(r for r in seen if r["tool"] == "get_learner_overview")
    assert overview["data"]["profile"]["exam_date"] and isinstance(overview["data"]["profile"]["created_at"], str)


def _rounds(run_agent, rounds):
    async def wrapper(**kwargs):
        kwargs["max_rounds"] = rounds
        return await run_agent(**kwargs)

    return wrapper
