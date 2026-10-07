"""Plans and milestones follow the content that exists; lessons and the error log stay linked (review wave 3)."""
from datetime import timedelta

from server import models
from server.services import insights, planner
from server.tests.test_personalization import next_monday_9am
from server.utils import timeutil


def add_task(db, phase: int, week: int, category: str, title: str) -> models.SprintTask:
    roadmap = db.query(models.Roadmap).filter_by(user_id=1).one()
    task = models.SprintTask(roadmap_id=roadmap.id, phase=phase, week_number=week, category=category, title=title)
    db.add(task)
    db.commit()
    return task


def test_milestones_without_content_are_flagged_and_not_pushed(client, seeded, db):
    part7 = add_task(db, 2, 1, "Reading", "Kỹ thuật 3-Pass Scanning cho Part 7 đoạn đơn")
    full = add_task(db, 3, 1, "Test", "Full Test 1 ETS 2024 (120 phút áp lực thật)")
    vocab = add_task(db, 1, 1, "Vocab", "Hoàn thành 300 từ vựng kinh doanh cốt lõi ETS")
    listening = add_task(db, 1, 1, "Listening", "Dictation 10 câu hỏi Part 2 (Dạng Who/Where/When)")

    tasks = {t["id"]: t for t in client.get("/api/roadmaps").json()["tasks"]}
    assert tasks[part7.id]["content_note"] == "Chưa có đề Part 7"
    assert tasks[full.id]["content_note"] == "Chưa có đề full 200 câu"
    assert tasks[vocab.id]["content_note"] == "Kho mới có 5 thẻ"
    assert tasks[listening.id]["content_note"] is None  # Part 2 exists in the bank

    roadmap = db.query(models.Roadmap).filter_by(user_id=1).one()
    pushed = insights.milestone_task(roadmap, insights.content_gaps(db, roadmap.tasks))
    assert pushed is not None and pushed["key"] not in {f"roadmap-{t.id}" for t in (part7, full, vocab)}


def test_phases_come_from_the_rescaled_milestones_and_the_learner_target(client, seeded):
    client.patch("/api/learner/profile", json={"baseline_listening": 300, "baseline_reading": 250, "target_score": 850})
    roadmap = client.get("/api/roadmaps").json()
    phases = roadmap["phases"]
    assert [p["phase"] for p in phases] == [1, 2] and phases[0]["start_week"] == 1 and phases[-1]["end_week"] == roadmap["total_weeks"]
    assert phases[0]["end_week"] == 8  # seeded phase 2 starts in week 9
    assert phases[-1]["goal_score"] == 850 and 550 < phases[0]["goal_score"] < 850
    assert roadmap["current_phase"] == 1


def test_generated_roadmap_title_follows_rescaling(client, seeded, db):
    roadmap = db.query(models.Roadmap).filter_by(user_id=1).one()
    roadmap.title = "Lộ trình 24 tuần Chinh phục TOEIC 800+"
    db.commit()
    exam = timeutil.local_today() + timedelta(days=70)
    client.patch("/api/learner/profile", json={"exam_date": exam.isoformat(), "target_score": 900})
    assert client.get("/api/roadmaps").json()["title"] == "Lộ trình 10 tuần Chinh phục TOEIC 900+"
    client.patch("/api/roadmaps", json={"title": "Lộ trình của tôi"})
    client.patch("/api/learner/profile", json={"target_score": 850})
    assert client.get("/api/roadmaps").json()["title"] == "Lộ trình của tôi"  # a title the learner wrote is kept


def test_listening_task_names_the_parts_that_have_audio(client, seeded):
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    client.patch("/api/learner/profile", json={"study_days": list(range(7)), "daily_goal_minutes": 120})
    items = [i for d in client.post("/api/plan/replan").json()["days"] for i in d["items"] if i["kind"] == "listening"]
    assert items and all(i["title"] == "Dictation & Shadowing Part 2" for i in items)  # seeded bank: Part 2 only


def test_no_listening_task_without_listening_content(client, seeded, db):
    db.query(models.TestQuestion).filter(models.TestQuestion.part == "Part 2").delete()
    db.commit()
    start, _ = next_monday_9am()
    timeutil.set_now(start)
    client.patch("/api/learner/profile", json={"study_days": list(range(7)), "daily_goal_minutes": 120})
    kinds = {i["kind"] for d in client.post("/api/plan/replan").json()["days"] for i in d["items"]}
    assert "listening" not in kinds


def test_manual_entry_for_a_logged_question_updates_that_log(client, seeded, db):
    client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[108], "choice": "B"}], "mode": "study"})
    manual = client.post("/api/error-logs", json={
        "test_id": "ETS2024_01", "part": "Part 5", "question_no": 108, "error_type": "vocab",
        "root_cause": "Không biết nghĩa của unanimous", "key_rule_or_paraphrase": "unanimous = agreed by all",
    })
    assert manual.status_code == 201
    logs = db.query(models.ErrorLog).filter_by(user_id=1, question_id=seeded[108]).all()
    assert len(logs) == 1 and logs[0].source == "manual" and logs[0].error_type == "VOCAB"
    assert logs[0].root_cause == "Không biết nghĩa của unanimous"


def test_lesson_list_shows_completion(client, seeded):
    client.post("/api/knowledge/lessons/1/progress", json={"event": "complete"})
    lessons = {item["lesson_number"]: item for item in client.get("/api/knowledge/lessons").json()}
    assert lessons[1]["completed"] is True and lessons[2]["completed"] is False


def test_weekly_goal_is_judged_against_the_planned_minutes(client, seeded, db):
    start, monday = next_monday_9am()
    timeutil.set_now(start)
    client.patch("/api/learner/profile", json={"study_days": list(range(7)), "daily_goal_minutes": 300})
    client.post("/api/plan/replan")
    planned = sum(
        i.estimated_minutes or 0
        for i in db.query(models.StudyPlanItem).filter(models.StudyPlanItem.user_id == 1, models.StudyPlanItem.plan_date == monday)
    )
    assert 0 < planned < 300  # the plan caps its blocks
    timeutil.set_now(start + timedelta(days=1))
    report = client.get("/api/learner/weekly-report").json()
    assert report["study"]["goal_minutes"] <= planned


def test_planner_listening_parts_helper_matches_the_bank(seeded, db):
    report = planner.skills_service.compute(db, 1)
    assert [p for p in ("Part 1", "Part 2", "Part 3", "Part 4") if report.parts[p].question_count] == ["Part 2"]
