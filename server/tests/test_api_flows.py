from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from server import models
from server.database import engine, init_db
from server.services import reminder_service, scoring
from server.utils import timeutil


def submit(client, answers: dict, question_ids, **extra):
    payload = {"answers": {str(k): v for k, v in answers.items()}, "question_ids": list(question_ids), **extra}
    response = client.post("/api/tests/ETS2024_01/submit", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------------------- system
def test_health_cors_and_legacy_routes(client):
    health = client.get("/api/health").json()
    assert health["database"] == "ok" and health["ai"]["offline"] is True

    allowed = client.options(
        "/api/dashboard/stats",
        headers={"Origin": "http://localhost:3005", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3005"
    blocked = client.options(
        "/api/dashboard/stats",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in blocked.headers

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307 and root.headers["location"] == "/legacy/"
    redirect = client.get("/toeic_study_guide.html", follow_redirects=False)
    assert redirect.status_code == 307 and redirect.headers["location"] == "/legacy/toeic_study_guide.html"
    assert client.get("/legacy/").status_code == 200


def test_tts_rejects_bad_input_before_any_network_call(client):
    assert client.get("/api/tts", params={"text": "hi", "voice": "evil-voice"}).status_code == 422
    assert client.get("/api/tts", params={"text": "hi", "rate": "+500%"}).status_code == 422


def test_migration_adds_missing_columns_idempotently():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE error_logs"))
        conn.execute(
            text(
                "CREATE TABLE error_logs (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, test_id VARCHAR(50), "
                "part VARCHAR(20) NOT NULL, question_no INTEGER, error_type VARCHAR(20) NOT NULL, user_choice VARCHAR(10), "
                "correct_choice VARCHAR(10), question_content TEXT, image_url VARCHAR(255), root_cause TEXT NOT NULL, "
                "key_rule_or_paraphrase TEXT, status VARCHAR(20), review_count INTEGER, created_at DATETIME)"
            )
        )
    added = init_db()
    assert {"error_logs.topic", "error_logs.question_id", "error_logs.source"} <= set(added)
    assert init_db() == []


# --------------------------------------------------------------------------- SRS
def test_due_queue_respects_schedule_and_daily_new_quota(client, seeded, db):
    due = client.get("/api/flashcards/due").json()
    assert len(due) == 3  # 5 new cards, SRS_NEW_CARDS_PER_DAY=3 in tests
    card_id = due[0]["card_id"]

    reviewed = client.post(f"/api/flashcards/{card_id}/review", json={"rating": 3}).json()
    assert reviewed["state"] == "review" and reviewed["interval_days"] == 2

    due_after = client.get("/api/flashcards/due").json()
    assert card_id not in [item["card_id"] for item in due_after]
    assert len(due_after) == 2  # quota: 3 - 1 new card introduced today

    summary = client.get("/api/flashcards/summary").json()
    assert summary["reviewed_today"] == 1 and summary["due_cards"] == 2 and summary["review_due"] == 0
    assert "category_stats" in summary and len(summary["category_stats"]) > 0

    srs = db.query(models.UserCardSRS).filter_by(card_id=card_id).one()
    srs.next_review_at = timeutil.utcnow() - timedelta(hours=1)
    db.commit()
    assert client.get("/api/flashcards/due").json()[0]["card_id"] == card_id  # overdue reviews come first

    # Topic-specific due queue and cram mode
    first_cat = summary["category_stats"][0]["category"]
    cat_due = client.get(f"/api/flashcards/due?category={first_cat}").json()
    assert all(c["flashcard"]["category"] == first_cat for c in cat_due)

    cram_due = client.get("/api/flashcards/due?mode=all&limit=50").json()
    assert len(cram_due) >= len(cat_due)

    stats = client.get("/api/dashboard/stats").json()
    today = next(day for day in stats["activity_week"] if day["is_today"])
    assert today["srs_reviews"] == 1 and today["active"] is True
    assert stats["srs_reviewed_today"] == 1 and stats["streak_days"] >= 1
    assert client.post("/api/flashcards/999/review", json={"rating": 3}).status_code == 404


def test_flashcard_create_dedupe_delete_and_ai_fill_offline(client, seeded, admin):
    assert client.post("/api/flashcards", json={"word": "Allocate", "meaning": "x", "example_sentence": "y"}).status_code == 409
    created = client.post(
        "/api/flashcards",
        json={"word": "Leverage", "meaning": "tận dụng", "example_sentence": "We leverage data.", "ipa": "/ˈlev.ər.ɪdʒ/"},
    )
    assert created.status_code == 201 and created.json()["ipa"] == "ˈlev.ər.ɪdʒ"
    assert client.get("/api/flashcards/summary").json()["new_cards"] == 6

    assert client.post("/api/flashcards/ai-fill", json={"word": "synergy"}).status_code == 503
    assert client.post("/api/flashcards/ai-fill", json={"word": "postpone"}).status_code == 409

    card_id = created.json()["id"]
    assert created.json()["example_translation"] is None

    # Test sentence translate endpoint (offline fallback when no keys in test environment)
    trans_resp = client.post("/api/flashcards/translate-sentence", json={"sentence": "We leverage data."})
    assert trans_resp.status_code == 200
    assert "translation" in trans_resp.json()

    # Test card translate-example
    trans_card = client.post(f"/api/flashcards/{card_id}/translate-example")
    assert trans_card.status_code == 200
    assert trans_card.json()["example_translation"] is not None

    assert client.delete(f"/api/flashcards/{card_id}").status_code == 401  # shared bank: admins only
    assert client.delete(f"/api/flashcards/{card_id}", headers=admin["headers"]).status_code == 200
    assert client.get("/api/flashcards/summary").json()["new_cards"] == 5


# --------------------------------------------------------------------------- quiz -> error log -> gaps -> lessons -> dashboard
def test_quiz_submission_feeds_error_log_gaps_lessons_and_dashboard(client, seeded):
    # Pin to a study day (Monday) so planner schedules practice tasks deterministically
    today = timeutil.local_today()
    monday = today - timedelta(days=today.weekday())
    timeutil.set_now(timeutil.local_datetime_utc(monday, 9, 0))

    questions = client.get("/api/tests/ETS2024_01/questions", params={"part": "Part 5"}).json()
    assert [q["question_no"] for q in questions] == [101, 108, 111]
    ids = {q["question_no"]: q["id"] for q in questions}
    assert questions[1]["trap_tag"] == "Bẫy Vị Trí Trạng Từ" and questions[1]["lesson_number"] == 1

    result = submit(client, {ids[101]: "B", ids[108]: "B"}, ids.values(), part="Part 5", time_spent_seconds=90)
    assert (result["correct_count"], result["total_questions"], result["unanswered"], result["errors_logged"]) == (1, 3, 1, 2)
    by_no = {r["question_no"]: r for r in result["results"]}
    assert by_no[108]["error_type"] == "GRAMMAR" and by_no[108]["error_log_id"]
    assert by_no[111]["error_type"] == "TIME" and by_no[111]["user_choice"] is None
    assert result["scaled_reading"] == scoring.reading_scaled(33)
    assert {gap["topic"]: gap["lesson_number"] for gap in result["learning_gaps"]} == {
        "Bẫy Vị Trí Trạng Từ": 1,
        "Bẫy Liên Từ vs Giới Từ": 2,
    }

    logs = client.get("/api/error-logs").json()
    assert {log["question_no"] for log in logs} == {108, 111}
    assert all(log["source"] == "mock_test" and log["correct_choice"] for log in logs)

    stats = client.get("/api/dashboard/stats").json()
    assert stats["open_errors"] == 2 and stats["rca_breakdown"]["GRAMMAR"] == 1 and stats["rca_breakdown"]["TIME"] == 1
    assert stats["recommended_lesson"]["lesson_number"] in (1, 2)
    assert stats["latest_submission"]["accuracy"] == pytest.approx(1 / 3, abs=1e-3)
    practice = [t for t in stats["today_tasks"] if t["kind"] == "practice"]
    assert practice and practice[0]["lesson_number"] in (1, 2) and practice[0]["auto"]
    assert practice[0]["progress"] >= 1  # today's answers already count toward the plan
    assert stats["top_learning_gaps"]  # legacy field is fed by the same data

    lesson1 = client.get("/api/knowledge/lessons").json()[0]["stats"]
    assert (lesson1["question_count"], lesson1["answered"], lesson1["accuracy"], lesson1["status"], lesson1["open_errors"]) == (
        2, 2, 0.5, "weak", 1,
    )
    detail = client.get("/api/knowledge/lessons/1").json()
    assert {q["question_no"] for q in detail["questions"]} == {101, 108} and detail["content_md"] == "## Nội dung"
    assert [q["question_no"] for q in client.get("/api/tests/ETS2024_01/questions", params={"lesson": 2}).json()] == [111]


def test_retakes_dedupe_errors_resolve_gaps_and_respect_manual_rca(client, seeded):
    ids = {n: seeded[n] for n in (101, 108, 111)}
    submit(client, {ids[101]: "B", ids[108]: "B", ids[111]: "C"}, ids.values())
    logs = {log["question_no"]: log for log in client.get("/api/error-logs").json()}
    assert set(logs) == {108, 111}

    # The learner rewrites the RCA by hand -> automated retakes must not overwrite it
    edited = client.patch(f"/api/error-logs/{logs[108]['id']}", json={"root_cause": "Quên quy tắc trạng từ", "error_type": "vocab"}).json()
    assert edited["error_type"] == "VOCAB" and edited["source"] == "manual"

    retake = submit(client, {ids[101]: "B", ids[108]: "C", ids[111]: "C"}, ids.values())
    assert retake["errors_logged"] == 2
    logs_after = {log["question_no"]: log for log in client.get("/api/error-logs").json()}
    assert len(logs_after) == 2 and logs_after[108]["root_cause"] == "Quên quy tắc trạng từ"

    client.patch(f"/api/error-logs/{logs_after[111]['id']}", json={"status": "mastered"})
    topics = [gap["topic"] for gap in client.get("/api/dashboard/stats").json()["learning_gaps"]]
    assert "Bẫy Liên Từ vs Giới Từ" not in topics and "Bẫy Vị Trí Trạng Từ" in topics

    submit(client, {ids[111]: "B"}, [ids[111]])  # wrong again after mastering -> reopened, not duplicated
    reopened = [log for log in client.get("/api/error-logs").json() if log["question_no"] == 111]
    assert len(reopened) == 1 and reopened[0]["status"] == "unresolved"

    assert client.post("/api/tests/ETS2024_01/submit", json={"answers": {}, "question_ids": [99999]}).status_code == 422


def test_manual_error_log_is_enriched_from_question_bank(client, seeded):
    created = client.post(
        "/api/error-logs",
        json={"test_id": "ETS2024_01", "part": "5", "question_no": 108, "error_type": "grammar", "root_cause": "Nhầm", "user_choice": "b"},
    )
    assert created.status_code == 201
    data = created.json()
    assert (data["correct_choice"], data["topic"], data["question_id"], data["user_choice"], data["part"]) == (
        "D", "Bẫy Vị Trí Trạng Từ", seeded[108], "B", "Part 5",
    )
    assert client.get("/api/dashboard/stats").json()["learning_gaps"][0]["topic"] == "Bẫy Vị Trí Trạng Từ"
    base = {"part": "Part 5", "root_cause": "x"}
    assert client.post("/api/error-logs", json={**base, "error_type": "WRONG"}).status_code == 422
    assert client.post("/api/error-logs", json={**base, "error_type": "TRAP", "user_choice": "E"}).status_code == 422
    assert client.get("/api/tests/ETS2024_01/questions/108").json()["correct_choice"] == "D"


def test_legacy_ui_payloads_are_accepted(client, seeded):
    # docs/index.html mini-test posts error_code/remedy_rule (these requests used to fail with 422)
    legacy = client.post(
        "/api/error-logs",
        json={"test_id": "ETS2024_01", "part": "Part 5", "question_no": 101, "error_code": "GRAMMAR",
              "user_choice": "(a)", "correct_choice": "B", "root_cause": "Bẫy từ loại", "remedy_rule": "speak clearly"},
    )
    assert legacy.status_code == 201, legacy.text
    assert (legacy.json()["error_type"], legacy.json()["user_choice"], legacy.json()["key_rule_or_paraphrase"]) == ("GRAMMAR", "A", "speak clearly")
    chat = client.post("/api/ai/chat", json={"message": "Xin chào", "image_base64": None, "history": [{"role": "user", "content": "x"}]})
    assert chat.status_code == 200
    stats = client.get("/api/dashboard/stats").json()
    assert {"srs_due_count", "srs_mastered_count", "roadmap_percent", "total_errors", "total_flashcards"} <= stats.keys()


# --------------------------------------------------------------------------- roadmap & profile
def test_roadmap_week_follows_start_date_and_tasks_are_owned(client, seeded, db):
    roadmap = client.get("/api/roadmaps").json()
    assert roadmap["current_week"] == 1 and roadmap["progress_percent"] == 33

    start = (timeutil.local_today() - timedelta(days=15)).isoformat()
    moved = client.patch("/api/roadmaps", json={"start_date": start}).json()
    assert moved["current_week"] == 3 and moved["current_phase"] == 1
    assert client.get("/api/dashboard/stats").json()["current_week"] == 3

    other = models.User(id=2, username="other")
    db.add(other)
    db.flush()
    other_roadmap = models.Roadmap(user_id=2, title="Other roadmap", total_weeks=24)
    db.add(other_roadmap)
    db.flush()
    foreign = models.SprintTask(roadmap_id=other_roadmap.id, week_number=1, category="Vocab", title="Not yours")
    db.add(foreign)
    db.commit()
    assert client.patch(f"/api/roadmaps/tasks/{foreign.id}", json={"is_completed": True}).status_code == 404

    own = next(task for task in roadmap["tasks"] if not task["is_completed"])
    assert client.patch(f"/api/roadmaps/tasks/{own['id']}", json={"is_completed": True}).json()["completed_at"]
    assert client.get("/api/roadmaps").json()["progress_percent"] == 67


def test_profile_update_flows_into_dashboard_and_score_calculator(client, seeded):
    me = client.patch("/api/users/me", json={"display_name": "Ryan", "headline": "Backend Engineer", "target_score": 850}).json()
    assert me["target_cefr"].startswith("B2")
    stats = client.get("/api/dashboard/stats").json()
    assert (stats["display_name"], stats["target_score"], stats["headline"]) == ("Ryan", 850, "Backend Engineer")
    calc = client.post("/api/tests/calculate-score", json={"raw_listening": 80, "raw_reading": 80}).json()
    assert calc["target_score"] == 850 and calc["recommendations"]
    assert client.patch("/api/users/me", json={"target_score": 2000}).status_code == 422
    assert client.post("/api/tests/calculate-score", json={"raw_listening": 120, "raw_reading": 0}).status_code == 422


# --------------------------------------------------------------------------- reminders
def test_reminder_crud_and_due_window(client, seeded):
    created = client.post("/api/reminders", json={"scheduled_time": "21:00", "message": "Ôn bài"})
    assert created.status_code == 201
    assert client.post("/api/reminders", json={"scheduled_time": "25:00", "message": "x"}).status_code == 422
    rid = created.json()["id"]
    assert client.patch(f"/api/reminders/{rid}", json={"is_active": False}).json()["is_active"] is False
    assert client.delete(f"/api/reminders/{rid}").status_code == 200

    tz = timeutil.app_tz()
    reminder = models.StudyReminder(user_id=1, reminder_type="daily_study", scheduled_time="21:00", message="x", is_active=True)
    at = lambda h, m: datetime(2026, 10, 1, h, m, tzinfo=tz)  # noqa: E731
    assert reminder_service.is_due(reminder, at(21, 10))
    assert not reminder_service.is_due(reminder, at(20, 59))
    assert not reminder_service.is_due(reminder, at(22, 30))  # outside the grace window
    reminder.last_triggered_at = at(21, 5).astimezone(timezone.utc).replace(tzinfo=None)
    assert not reminder_service.is_due(reminder, at(21, 10))  # already sent today
    assert reminder_service.dispatch_enabled() is False  # no Telegram config in tests
