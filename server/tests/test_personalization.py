"""Personalization: tracking, skill model, spaced review of mistakes, adaptive plan, coach."""
from datetime import timedelta

import pytest

from server import models
from server.utils import timeutil


def next_monday_9am():
    """A frozen 'now' that is always after the real clock (seeded rows are created with real time)."""
    today = timeutil.local_today()
    monday = today + timedelta(days=7 - today.weekday())
    return timeutil.local_datetime_utc(monday, 9, 0), monday


def lesson(insights: dict, number: int) -> dict:
    return next(item for item in insights["lessons"] if item["lesson_number"] == number)


def submit(client, answers, **extra):
    response = client.post("/api/practice/submit", json={"answers": answers, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_attempts_and_study_time_are_tracked(client, seeded):
    start, monday = next_monday_9am()
    timeutil.set_now(start)
    result = submit(client, [
        {"question_id": seeded[101], "choice": "B", "time_ms": 18000},
        {"question_id": seeded[108], "choice": "A", "time_ms": 42000},
        {"question_id": seeded[111], "choice": None, "time_ms": 30000},
    ], mode="exam")
    assert (result["correct_count"], result["time_spent_seconds"], result["avg_time_seconds"], result["mode"]) == (1, 90, 30.0, "exam")
    assert {r["question_id"]: r["time_ms"] for r in result["results"]}[seeded[108]] == 42000

    timeutil.advance(minutes=5)
    for card in client.get("/api/flashcards/due").json()[:2]:
        assert client.post(f"/api/flashcards/{card['card_id']}/review", json={"rating": 3, "duration_ms": 15000}).status_code == 200
        timeutil.advance(seconds=20)
    client.post("/api/knowledge/lessons/1/progress", json={"event": "view"})
    progress = client.post("/api/knowledge/lessons/1/progress", json={"event": "heartbeat", "seconds": 120}).json()
    assert progress["view_count"] == 1 and progress["time_spent_seconds"] == 120

    data = client.get("/api/learner/insights").json()
    today = data["study_minutes"][-1]
    assert today["date"] == monday.isoformat()
    assert today["minutes"] == 4  # practice 90s + 2 cards x 15s (one merged SRS session) + lesson 120s
    assert set(today["by_kind"]) == {"practice", "srs", "lesson"}
    assert lesson(data, 1)["attempts"] == 2 and lesson(data, 1)["avg_time_seconds"] == 30.0
    part5 = next(p for p in data["parts"] if p["part"] == "Part 5")
    assert part5["attempts"] == 3 and part5["avg_time_seconds"] == 30.0  # blank answers do not count for pace

    dash = client.get("/api/dashboard/stats").json()
    assert dash["study_minutes_today"] == 4 and dash["total_attempts"] == 3
    assert next(d for d in dash["activity_week"] if d["is_today"])["minutes"] == 4


def test_mistakes_follow_spaced_review_until_mastered(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    question = seeded[111]

    def answer(choice, mode="practice"):
        return submit(client, [{"question_id": question, "choice": choice}], mode=mode)["results"][0]

    assert answer("C")["error_log_id"]
    assert client.get("/api/practice/review-queue").json() == []  # first review is tomorrow
    log = client.get("/api/error-logs").json()[0]
    assert log["review_stage"] == 0 and log["next_review_at"]

    timeutil.advance(days=1)
    queue = client.get("/api/practice/review-queue").json()
    assert [q["id"] for q in queue] == [question] and queue[0]["review_stage"] == 0
    dash = client.get("/api/dashboard/stats").json()
    assert dash["error_reviews_due"] == 1
    review_task = next(t for t in dash["today_tasks"] if t["kind"] == "error_review")
    assert review_task["done"] is False
    assert answer("A", "review")["review_outcome"] == "advanced"
    review_task = next(t for t in client.get("/api/dashboard/stats").json()["today_tasks"] if t["kind"] == "error_review")
    assert review_task["done"] is True and review_task["auto"] is True

    timeutil.advance(days=1)  # stage 1 waits 3 days: a correct answer now changes nothing
    assert client.get("/api/practice/review-queue").json() == []
    assert answer("A")["review_outcome"] == "early"

    timeutil.advance(days=2)
    assert answer("A", "review")["review_outcome"] == "advanced"
    log = client.get("/api/error-logs").json()[0]
    assert (log["review_stage"], log["status"]) == (2, "reviewed")

    timeutil.advance(days=7)
    assert answer("A", "review")["review_outcome"] == "mastered"
    assert client.get("/api/error-logs").json()[0]["status"] == "mastered"
    assert client.get("/api/dashboard/stats").json()["learning_gaps"] == []

    timeutil.advance(days=1)  # a new mistake re-opens the same log at stage 0
    assert answer("B")["review_outcome"] == "reset"
    logs = client.get("/api/error-logs").json()
    assert len(logs) == 1 and (logs[0]["status"], logs[0]["review_stage"]) == ("unresolved", 0)


def test_mastery_uses_baseline_prior_recency_and_feeds_prediction(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    assert client.patch("/api/learner/profile", json={"baseline_reading": 300, "baseline_listening": 350}).status_code == 200
    data = client.get("/api/learner/insights").json()
    assert data["prediction"]["reading"]["basis"] == "baseline" and data["prediction"]["listening"]["basis"] == "baseline"
    assert abs(data["prediction"]["reading"]["expected"] - 300) <= 15 and abs(data["prediction"]["listening"]["expected"] - 350) <= 15
    baseline_reading = data["prediction"]["reading"]["expected"]
    assert lesson(data, 1)["status"] == "not_started" and lesson(data, 1)["prior"] == data["priors"]["reading"]

    answers = [{"question_id": seeded[101], "choice": "B"}, {"question_id": seeded[108], "choice": "D"}]
    submit(client, answers)
    first = lesson(client.get("/api/learner/insights").json(), 1)["mastery"]
    for _ in range(2):  # immediate retakes of the same questions measure memory, not skill
        timeutil.advance(hours=1)
        submit(client, answers)
    assert lesson(client.get("/api/learner/insights").json(), 1)["mastery"] == pytest.approx(first, abs=0.02)

    timeutil.advance(days=1)  # a day later the same questions are fresh evidence again
    submit(client, answers)
    data = client.get("/api/learner/insights").json()
    l1 = lesson(data, 1)
    assert l1["mastery"] > first and l1["status"] == "improving"  # only 2 distinct questions: not "strong" yet
    assert l1["attempts"] == 8
    assert data["prediction"]["reading"]["basis"] == "partial"  # Part 5 measured, Part 6/7 extrapolated
    assert data["prediction"]["reading"]["expected"] > baseline_reading and data["prediction"]["confidence"] > 0

    timeutil.advance(days=120)  # old evidence fades back toward the prior
    l1 = lesson(client.get("/api/learner/insights").json(), 1)
    assert l1["mastery"] < 0.7 and l1["confidence"] < 0.1


def test_onboarding_rescales_roadmap_and_builds_a_budgeted_plan(client, seeded):
    start, monday = next_monday_9am()
    timeutil.set_now(start)
    client.patch("/api/roadmaps", json={"start_date": monday.isoformat()})
    response = client.post("/api/learner/onboarding", json={
        "display_name": "Ryan", "target_score": 850, "exam_date": (monday + timedelta(days=42)).isoformat(),
        "baseline_reading": 300, "baseline_listening": 350, "daily_goal_minutes": 30, "study_days": [0, 1, 2, 3, 4],
        "new_cards_per_day": 10, "explanation_style": "concise", "focus_parts": ["Part 5"], "weak_areas": "Hay nhầm liên từ và giới từ",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    profile = data["profile"]
    assert profile["onboarded"] and profile["days_to_exam"] == 42 and profile["study_days"] == [0, 1, 2, 3, 4]
    assert profile["focus_parts"] == ["Part 5"] and profile["explanation_style"] == "concise"

    roadmap = client.get("/api/roadmaps").json()
    assert (roadmap["total_weeks"], roadmap["base_total_weeks"]) == (6, 24)
    weeks = {t["title"]: t["week_number"] for t in roadmap["tasks"]}
    assert weeks["Shadowing Part 3"] == 3  # base week 9 of 24 -> week 3 of 6

    days = data["plan"]["days"]
    assert [d["is_study_day"] for d in days] == [True] * 5 + [False] * 2
    assert not days[5]["items"] and not days[6]["items"]  # weekend off
    assert all(d["planned_minutes"] <= 30 + 3 for d in days)
    srs = next(i for i in days[0]["items"] if i["kind"] == "srs")
    assert srs["target_count"] == 5 and "5 thẻ mới" in srs["detail"]  # only 5 new cards exist (quota 10)
    assert not any(i["kind"] == "srs" for i in days[1]["items"])  # nothing left to introduce or review tomorrow
    practice = next(i for i in days[0]["items"] if i["kind"] == "practice")
    assert practice["lesson_number"] == 2 and "Theo lộ trình" in practice["reason"]

    memories = client.get("/api/learner/memories").json()
    assert memories[0]["pinned"] and "liên từ" in memories[0]["content"] and memories[0]["source"] == "onboarding"
    dash = client.get("/api/dashboard/stats").json()
    assert dash["onboarded"] and dash["days_to_exam"] == 42 and dash["srs_new_cards_per_day"] == 10


def test_plan_targets_weakest_lesson_and_completes_itself(client, seeded):
    start, monday = next_monday_9am()
    timeutil.set_now(start - timedelta(days=1))  # Sunday: diagnostic
    client.patch("/api/roadmaps", json={"start_date": monday.isoformat()})
    for _ in range(2):
        submit(client, [{"question_id": seeded[101], "choice": "B"}, {"question_id": seeded[108], "choice": "D"},
                        {"question_id": seeded[111], "choice": "C"}])

    timeutil.set_now(start)  # Monday
    week = client.get("/api/plan/week").json()
    assert week["focus"][0]["lesson_number"] == 2
    today = week["days"][0]["items"]
    practice = next(i for i in today if i["kind"] == "practice")
    assert practice["lesson_number"] == 2 and practice["status"] == "pending" and "lỗi chưa khắc phục" in practice["reason"]
    assert next(i for i in today if i["kind"] == "error_review")["status"] == "pending"

    submit(client, [{"question_id": seeded[111], "choice": "A"}], lesson_number=2)  # the drill also reviews the mistake
    items = client.get("/api/plan/week").json()["days"][0]["items"]
    drill = next(i for i in items if i["kind"] == "practice" and i["lesson_number"] == 2)
    assert drill["status"] == "done" and drill["auto"]
    assert next(i for i in items if i["kind"] == "error_review")["status"] == "done"
    assert any(i["kind"] == "practice" and i["lesson_number"] == 1 and i["status"] == "pending" for i in items)  # 2nd focus

    other = next(i for i in today if i["kind"] not in ("practice", "error_review", "srs"))
    assert client.delete(f"/api/plan/items/{other['id']}").json()["status"] == "skipped"
    custom = client.post("/api/plan/items", json={"title": "Đọc 1 email Part 7", "plan_date": monday.isoformat(), "estimated_minutes": 10}).json()
    assert custom["source"] == "user" and custom["kind"] == "custom"
    replanned = client.post("/api/plan/replan").json()["days"][0]["items"]
    ids = {i["id"] for i in replanned}
    assert custom["id"] in ids and other["id"] in ids
    assert [i["kind"] for i in replanned].count(other["kind"]) == 1  # skipped item is not re-added
    assert client.patch(f"/api/plan/items/{custom['id']}", json={"status": "done"}).json()["status"] == "done"


def test_plan_shifts_to_timed_mock_tests_near_the_exam(client, seeded):
    start, monday = next_monday_9am()
    timeutil.set_now(start)
    response = client.patch("/api/learner/profile", json={"exam_date": (monday + timedelta(days=5)).isoformat(), "study_days": list(range(7))})
    assert response.status_code == 200, response.text
    days = client.get("/api/plan/week").json()["days"]
    assert not days[5]["items"] and not days[6]["items"]  # exam day itself and after: no homework
    kinds = [{i["kind"] for i in d["items"]} for d in days[:5]]
    assert "mock" in kinds[0] and "lesson" not in set().union(*kinds)
    assert all("mock" in k and "practice" not in k for k in kinds[2:5])  # last 3 days: daily timed test, no new drills

    timeutil.set_now(start + timedelta(days=8))  # the exam is now in the past
    week = client.get("/api/plan/week").json()
    assert week["settings"]["exam_passed"] == (monday + timedelta(days=5)).isoformat() and week["settings"]["days_to_exam"] is None
    assert any(day["items"] for day in week["days"])  # planned as if no date was set, instead of an empty week
    assert client.get("/api/dashboard/stats").json()["exam_passed"] is True


def test_coach_suggests_and_executes_audited_actions(client, seeded, db):
    roadmap = db.query(models.Roadmap).first()
    task = models.SprintTask(roadmap_id=roadmap.id, phase=1, week_number=1, category="Syntax", title="Bài 01: ôn vị trí từ loại")
    db.add(task)
    db.commit()
    for _ in range(3):
        submit(client, [{"question_id": seeded[101], "choice": "B"}, {"question_id": seeded[108], "choice": "D"}])

    evidence = next(t for t in client.get("/api/roadmaps").json()["tasks"] if t["id"] == task.id)
    assert evidence["auto_met"] and evidence["evidence"].startswith("Đạt: Bài 01")

    suggestions = {s["id"]: s for s in client.get("/api/learner/suggestions").json()}
    assert "onboarding" in suggestions and "reminder" in suggestions
    milestone = suggestions[f"milestone_{task.id}"]
    assert (milestone["kind"], milestone["tool"]) == ("tool", "set_roadmap_task")

    result = client.post("/api/ai/actions/execute", json={"tool": milestone["tool"], "args": milestone["args"]}).json()
    assert result["status"] == "success" and result["undoable"]
    assert next(t for t in client.get("/api/roadmaps").json()["tasks"] if t["id"] == task.id)["is_completed"]
    action = client.get("/api/ai/actions").json()[0]
    assert (action["tool"], action["source"], action["status"]) == ("set_roadmap_task", "coach", "applied")

    assert client.post(f"/api/ai/actions/{result['action_id']}/undo").json()["status"] == "undone"
    assert not next(t for t in client.get("/api/roadmaps").json()["tasks"] if t["id"] == task.id)["is_completed"]
    assert client.post(f"/api/ai/actions/{result['action_id']}/undo").status_code == 409


def test_smart_set_puts_due_mistakes_first(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    submit(client, [{"question_id": seeded[111], "choice": "C"}, {"question_id": seeded[101], "choice": "B"}])
    timeutil.advance(days=1)
    smart = client.get("/api/practice/smart?count=4").json()
    assert smart[0]["id"] == seeded[111] and smart[0]["reason"].startswith("Ôn lại câu sai")
    assert any(q["reason"] == "Câu mới chưa làm" and q["id"] == seeded[14] for q in smart)
    assert len({q["id"] for q in smart}) == len(smart) == 4


def test_profile_validation(client, seeded):
    yesterday = (timeutil.local_today() - timedelta(days=1)).isoformat()
    assert client.patch("/api/learner/profile", json={"exam_date": yesterday}).status_code == 422
    assert client.patch("/api/learner/profile", json={"study_days": []}).status_code == 422
    assert client.patch("/api/learner/profile", json={"explanation_style": "funny"}).status_code == 422
    assert client.post("/api/learner/onboarding", json={"daily_goal_minutes": 5}).status_code == 422
    ok = client.patch("/api/users/me", json={"new_cards_per_day": 4, "focus_parts": ["part7", "Part 5", "7"]}).json()
    assert ok["new_cards_per_day"] == 4 and ok["focus_parts"] == ["Part 7", "Part 5"]
    assert len(client.get("/api/flashcards/due").json()) == 4  # the profile overrides SRS_NEW_CARDS_PER_DAY (3 in tests)
    client.patch("/api/users/me", json={"new_cards_per_day": 2})
    assert len(client.get("/api/flashcards/due").json()) == 2


def test_auto_adjust_lightens_the_plan_while_behind(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    assert client.patch("/api/learner/profile", json={"daily_goal_minutes": 60, "study_days": [0, 1, 2, 3, 4, 5, 6]}).status_code == 200
    week = client.get("/api/plan/week").json()
    assert (week["settings"]["planned_daily_minutes"], week["settings"]["adjustments"]) == (60, [])
    full_day = week["days"][0]["planned_minutes"]

    for _ in range(7):  # a week of opening the app without studying: planned items stay undone
        timeutil.advance(days=1)
        client.get("/api/plan/week")
    week = client.get("/api/plan/week").json()
    settings = week["settings"]
    assert week["history"]["behind"] is True and week["history"]["done_items"] == 0
    assert (settings["daily_minutes"], settings["planned_daily_minutes"]) == (60, 45)
    assert "kế hoạch nhẹ hơn" in settings["adjustments"][0]
    assert week["days"][0]["planned_minutes"] <= 45 and full_day <= 60

    # opting out restores the learner's own budget immediately (auto_adjust is a plan field)
    assert client.patch("/api/learner/profile", json={"auto_adjust": False}).status_code == 200
    week = client.get("/api/plan/week").json()
    assert (week["settings"]["planned_daily_minutes"], week["settings"]["adjustments"], week["settings"]["auto_adjust"]) == (60, [], False)


def test_plan_and_coach_never_ask_ai_to_write_questions(client, seeded, monkeypatch):
    """AGENTS.md rule 3: practice questions come only from the authentic bank, even when AI is online."""
    from server.services import ai_agent_service

    start, _ = next_monday_9am()
    timeutil.set_now(start)
    online = {**ai_agent_service.provider_status(), "offline": False, "provider": "deepseek"}
    monkeypatch.setattr(ai_agent_service, "provider_status", lambda: online)
    client.patch("/api/learner/profile", json={"study_days": [0, 1, 2, 3, 4, 5, 6]})
    kinds = [i["kind"] for d in client.post("/api/plan/replan").json()["days"] for i in d["items"]]
    assert "ai_generate" not in kinds
    assert not [s for s in client.get("/api/learner/suggestions").json() if s["id"].startswith("ai_practice")]


def test_weekly_report_compares_this_week_with_the_previous_one(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)  # week 1: two mistakes
    submit(client, [{"question_id": seeded[111], "choice": "B", "time_ms": 30000},
                    {"question_id": seeded[101], "choice": "A", "time_ms": 30000}], mode="practice", part="Part 5")

    timeutil.advance(days=7)  # week 2: the same topics answered correctly
    submit(client, [{"question_id": seeded[111], "choice": "A", "time_ms": 15000},
                    {"question_id": seeded[101], "choice": "B", "time_ms": 15000},
                    {"question_id": seeded[108], "choice": "D", "time_ms": 15000}], mode="smart")
    log = next(l for l in client.get("/api/error-logs").json() if l["question_no"] == 111)
    assert client.patch(f"/api/error-logs/{log['id']}", json={"status": "mastered"}).status_code == 200
    client.post("/api/knowledge/lessons/2/progress", json={"event": "heartbeat", "seconds": 300})

    timeutil.advance(days=2)
    report = client.get("/api/learner/weekly-report").json()
    practice = report["practice"]
    assert (practice["questions"], practice["accuracy"], practice["previous_accuracy"], practice["accuracy_delta"]) == (3, 1.0, 0.0, 1.0)
    changes = {c["lesson_number"]: c for c in report["mastery_changes"]}
    assert changes[2]["delta"] > 0.03 and changes[1]["delta"] > 0.03 and changes[2]["attempts"] == 1
    assert report["errors"]["mastered"] == 1 and report["errors"]["new"] == 0
    assert report["study"]["minutes"] >= 5
    assert any(h.startswith("Tiến bộ") and "Bài 02" in h for h in report["highlights"])
    assert report["markdown"].startswith("📊 *Báo cáo tuần") and report["recommendations"]

    tool = client.post("/api/ai/actions/execute", json={"tool": "get_weekly_report", "args": {}}).json()
    assert tool["status"] == "success" and tool["data"]["practice"]["questions"] == 3
    future = (timeutil.local_today() + timedelta(days=1)).isoformat()
    assert client.get(f"/api/learner/weekly-report?end={future}").status_code == 422


def test_manual_status_change_keeps_the_review_schedule_consistent(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    submit(client, [{"question_id": seeded[111], "choice": "B", "time_ms": 20000}])
    log = next(l for l in client.get("/api/error-logs").json() if l["question_no"] == 111)
    timeutil.advance(days=1)
    assert [q["id"] for q in client.get("/api/practice/review-queue").json()] == [seeded[111]]

    mastered = client.patch(f"/api/error-logs/{log['id']}", json={"status": "mastered"}).json()
    assert (mastered["review_stage"], mastered["next_review_at"]) == (3, None) and mastered["last_reviewed_at"]
    assert client.get("/api/practice/review-queue").json() == []

    reopened = client.patch(f"/api/error-logs/{log['id']}/status?status=unresolved").json()
    assert reopened["status"] == "unresolved" and reopened["review_stage"] == 0 and reopened["next_review_at"]


def test_reminders_carry_the_personal_plan_and_the_weekly_report(client, seeded, db):
    from server.services import reminder_service

    start, monday = next_monday_9am()
    timeutil.set_now(start)
    daily = client.post("/api/reminders", json={"scheduled_time": "09:00", "message": "Học thôi", "reminder_type": "daily_study"}).json()
    weekly = client.post("/api/reminders", json={"scheduled_time": "09:00", "message": "Tổng kết tuần", "reminder_type": "weekly_report"}).json()
    rows = {r.id: r for r in db.query(models.StudyReminder).all()}

    text = reminder_service.compose_message(db, rows[daily["id"]])
    assert "Kế hoạch hôm nay còn" in text and "thẻ SRS cần ôn" in text

    now_local = timeutil.local_now()
    assert reminder_service.is_due(rows[daily["id"]], now_local) and not reminder_service.is_due(rows[weekly["id"]], now_local)
    sunday = now_local + timedelta(days=6)
    assert sunday.weekday() == 6 and reminder_service.is_due(rows[weekly["id"]], sunday)
    report = reminder_service.compose_message(db, rows[weekly["id"]])
    assert report.startswith("Tổng kết tuần") and "📊 Báo cáo tuần" in report and "*" not in report
