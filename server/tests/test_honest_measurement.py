"""Numbers shown to the learner must reflect real skill (review wave 2)."""
from datetime import date, timedelta

import pytest

from server import models
from server.services import insights, listening_service, planner, scoring, skills
from server.services.srs_service import calculate_sm2_review


# --------------------------------------------------------------------------- SRS buttons
@pytest.mark.parametrize("repetition, interval", [(0, 1), (1, 2), (3, 20)])
def test_hard_good_easy_are_strictly_ordered(repetition, interval):
    hard, good, easy = (calculate_sm2_review(repetition, 2.5, interval, rating)[2] for rating in (2, 3, 4))
    assert hard < good < easy


def test_mastered_means_a_long_interval_not_many_taps():
    rep, ease, interval, state = 0, 2.5, 1, "new"
    for _ in range(4):  # four "Hard" in a row used to count as mastered
        rep, ease, interval, state, _ = calculate_sm2_review(rep, ease, interval, 2)
    assert state == "review" and interval < 21
    assert calculate_sm2_review(5, 2.5, 20, 3)[3] == "mastered"


# --------------------------------------------------------------------------- dictation
def test_dictation_normalises_typing_variants():
    for learner, target in (
        ("She’s waiting", "She's waiting"),      # curly apostrophe from iOS/macOS keyboards
        ("It is ten o'clock", "It's 10 o'clock"),  # contraction + number
        ("the work order", "the work-order"),    # hyphen
        ("Number seven. How old is this building?", "How old is this building?"),  # spoken item number
    ):
        assert listening_service.diff_transcription(learner, target)["accuracy"] == 100.0, learner


def test_dictation_extra_words_cost_points():
    padded = listening_service.diff_transcription("how old is this building building blah blah", "How old is this building?")
    assert padded["accuracy"] < 80 and sum(t["status"] == "extra" for t in padded["tokens"]) == 3


def test_part2_dictation_includes_the_three_responses(client, seeded, db):
    question = db.get(models.TestQuestion, seeded[14])
    exercise = next(e for e in client.get("/api/listening/exercises", params={"part": "Part 2"}).json() if e["id"] == question.id)
    assert exercise["target_transcript"].startswith(question.sentence) and "(A) a" in exercise["target_transcript"]
    question_only = client.post("/api/listening/check-dictation", json={"question_id": question.id, "learner_text": question.sentence}).json()
    assert question_only["total_words"] > len(question.sentence.split()) and question_only["accuracy"] < 100


# --------------------------------------------------------------------------- scores and prediction
def test_small_sets_get_no_section_score():
    assert scoring.estimate_section_scaled("listening", 6, 6) is None  # 6/6 on Part 1 is not a 495
    assert scoring.estimate_section_scaled("reading", 15, 15) is None
    assert scoring.estimate_section_scaled("reading", 24, 30) == scoring.reading_scaled(80)


def test_prediction_reports_what_the_bank_can_measure(client, seeded):
    client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[101], "choice": "B"}], "mode": "study"})
    prediction = client.get("/api/learner/insights").json()["prediction"]
    assert prediction["measured_parts"] == ["Part 5"]
    assert set(prediction["unmeasurable_parts"]) == {"Part 1", "Part 3", "Part 4", "Part 6", "Part 7"}
    assert prediction["coverage"] == pytest.approx((25 + 30) / 200)
    assert prediction["reading"]["basis"] == "partial" and prediction["reading"]["parts"]["Part 6"]["measurable"] is False


def test_test_milestones_need_a_real_exam(seeded, db):
    roadmap = db.query(models.Roadmap).filter_by(user_id=1).one()
    task = models.SprintTask(roadmap_id=roadmap.id, phase=3, week_number=21, category="Test", title="Full Test 2 & 3: đạt trên 770")
    db.add(task)
    db.commit()
    report = skills.compute(db, 1)
    inflated = {"total": {"expected": 900}, "confidence": 0.9}
    assert task.id not in planner.milestone_evidence(db, 1, roadmap, report, inflated)

    db.add(models.UserTestSubmission(user_id=1, test_id="ETS2024_01", mode="exam", total_scaled_score=785))
    db.commit()
    assert "785" in planner.milestone_evidence(db, 1, roadmap, report, inflated)[task.id]


# --------------------------------------------------------------------------- streak
def test_planned_rest_days_do_not_break_the_streak():
    monday = date(2026, 10, 5)
    active = {monday - timedelta(days=offset): {"x": 1} for offset in (1, 2, 3, 4, 5, 6)}  # Tue..Sat before, skip Sunday
    active.pop(monday - timedelta(days=1))  # Sunday: rest
    week_days = (0, 1, 2, 3, 4, 5)  # Mon-Sat
    assert insights.streak_from(active, monday, study_days=week_days) == 5
    assert insights.streak_from(active, monday) == 0  # without a schedule the rest day breaks it
