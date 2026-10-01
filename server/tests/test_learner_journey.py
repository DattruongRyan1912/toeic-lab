"""End-to-end learner journey over two simulated weeks.

Proves the personalization loop: diagnostic mistakes -> weakest lesson becomes the plan focus ->
daily plan items complete themselves from activity -> mistakes are reviewed 1-3-7 days later and
mastered -> mastery and predicted score rise -> streak and study minutes are tracked.
"""
from datetime import timedelta

from server import models
from server.utils import timeutil

from server.tests.test_personalization import lesson, next_monday_9am, submit


def add_lesson2_questions(db) -> list:
    sentences = [
        "___ the heavy rain, the outdoor team-building event went ahead as planned.",
        "The release was delayed ___ the QA team found a critical bug.",
        "___ the budget cuts, the department hired two new engineers.",
    ]
    ids = []
    for offset, sentence in enumerate(sentences):
        question = models.TestQuestion(
            test_id="ETS2024_01", part="Part 5", question_no=140 + offset, sentence=sentence, choice_a="Despite" if offset != 1 else "because",
            choice_b="Although" if offset != 1 else "because of", choice_c="Because" if offset != 1 else "despite", choice_d="Even if",
            correct_choice="A", explanation="Giới từ + cụm danh từ / liên từ + mệnh đề",
            distractor_analysis="[Bẫy Liên Từ vs Giới Từ] Cần nhìn phía sau chỗ trống",
        )
        db.add(question)
        db.flush()
        ids.append(question.id)
    db.commit()
    return ids


def test_two_week_learner_journey(client, seeded, db):
    extra = add_lesson2_questions(db)
    lesson2 = [seeded[111], *extra]
    start, monday = next_monday_9am()
    timeutil.set_now(start)
    client.patch("/api/roadmaps", json={"start_date": monday.isoformat()})
    onboarding = client.post("/api/learner/onboarding", json={
        "target_score": 800, "exam_date": (monday + timedelta(weeks=8)).isoformat(), "daily_goal_minutes": 40,
        "study_days": [0, 1, 2, 3, 4, 5], "baseline_reading": 300, "baseline_listening": 300, "new_cards_per_day": 2,
    })
    assert onboarding.status_code == 200, onboarding.text

    # Day 0 — timed diagnostic: lesson 1 right, every lesson-2 question wrong
    diagnostic = [{"question_id": seeded[101], "choice": "B", "time_ms": 20000}, {"question_id": seeded[108], "choice": "D", "time_ms": 25000}]
    diagnostic += [{"question_id": q, "choice": "C", "time_ms": 40000} for q in lesson2]
    assert submit(client, diagnostic, mode="exam")["errors_logged"] == 4
    day0 = client.get("/api/learner/insights").json()
    assert lesson(day0, 2)["status"] == "weak"
    assert client.get("/api/plan/week").json()["focus"][0]["lesson_number"] == 2
    reading0 = day0["prediction"]["reading"]["expected"]

    studied_days = 1
    for offset in range(1, 14):
        day = monday + timedelta(days=offset)
        timeutil.set_now(timeutil.local_datetime_utc(day, 20, 0))
        dash = client.get("/api/dashboard/stats").json()
        if day.weekday() == 6:
            assert not [t for t in dash["today_tasks"] if t["kind"] != "milestone"], "Sunday is a rest day"
            continue
        assert dash["today_tasks"], f"study day {day} has a plan"

        queue = client.get("/api/practice/review-queue").json()
        if queue:
            submit(client, [{"question_id": q["id"], "choice": q["correct_choice"], "time_ms": 15000} for q in queue], mode="review")
        submit(client, [{"question_id": q, "choice": "A", "time_ms": 18000} for q in lesson2], lesson_number=2)
        for card in client.get("/api/flashcards/due").json():
            client.post(f"/api/flashcards/{card['card_id']}/review", json={"rating": 3, "duration_ms": 12000})
        studied_days += 1

        tasks = client.get("/api/dashboard/stats").json()["today_tasks"]
        for task in tasks:
            if task["kind"] in ("srs", "error_review") or (task["kind"] == "practice" and task["lesson_number"] == 2):
                assert task["done"], (day, task["kind"], task["progress"], task["target"])
        assert all(t["auto"] for t in tasks if t["kind"] in ("srs", "error_review", "practice"))

    final = client.get("/api/learner/insights").json()
    assert lesson(final, 2)["mastery"] > lesson(day0, 2)["mastery"] + 0.4
    assert lesson(final, 2)["status"] in ("improving", "strong") and lesson(final, 2)["open_errors"] == 0
    assert final["prediction"]["reading"]["expected"] > reading0
    assert final["prediction"]["confidence"] > day0["prediction"]["confidence"]

    logs = client.get("/api/error-logs").json()
    assert len(logs) == 4 and all(log["status"] == "mastered" for log in logs)  # 1-3-7 day reviews completed
    dash = client.get("/api/dashboard/stats").json()
    assert dash["learning_gaps"] == [] and dash["error_reviews_due"] == 0
    assert dash["streak_days"] == 6  # Mon-Sat of week 2 (both Sundays were rest days)
    minutes = {item["date"]: item["minutes"] for item in final["study_minutes"]}
    assert sum(1 for value in minutes.values() if value > 0) == studied_days == 12
    assert client.get("/api/learner/insights").json()["srs_retention"]["reviews"] > 0
