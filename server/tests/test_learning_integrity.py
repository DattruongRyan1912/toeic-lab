"""Learning data must be recorded once, correctly, and only for real accounts (review wave 1)."""
import threading
from datetime import timedelta

from server import models
from server.database import SessionLocal
from server.services import curriculum, insights, maintenance, planner
from server.utils import timeutil


def counts(db) -> tuple:
    db.expire_all()
    return tuple(db.query(model).count() for model in (models.UserTestSubmission, models.QuestionAttempt, models.ErrorLog, models.SRSReviewLog, models.StudySession))


# --------------------------------------------------------------------------- listening time
def test_listening_time_is_saved(client, seeded, db):
    assert client.post("/api/listening/track", json={"seconds": 120}).json()["status"] == "tracked"
    sessions = db.query(models.StudySession).filter_by(user_id=1, kind="listening").all()
    assert [s.duration_seconds for s in sessions] == [120]


# --------------------------------------------------------------------------- guests are read-only
def test_guests_are_graded_but_nothing_is_saved(client, seeded, db, production_mode):
    before = counts(db)
    graded = client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[108], "choice": "B"}], "mode": "study"})
    assert graded.status_code == 200
    body = graded.json()
    assert body["submission_id"] is None and body["results"][0]["is_correct"] is False and body["errors_logged"] == 0
    exam = client.post("/api/tests/ETS2024_01/submit", json={"answers": {str(seeded[101]): "B"}, "question_ids": [seeded[101]]})
    assert exam.status_code == 200 and exam.json()["submission_id"] is None

    srs_before = db.query(models.UserCardSRS).filter_by(user_id=1, card_id=1).one().state
    assert client.post("/api/flashcards/1/review", json={"rating": 4}).status_code == 200
    assert client.post("/api/learner/activity", json={"kind": "lesson", "seconds": 60}).json()["status"] == "ignored"
    assert client.post("/api/listening/track", json={"seconds": 60}).json()["status"] == "ignored"
    assert client.post("/api/knowledge/lessons/1/progress", json={"event": "view", "seconds": 30}).status_code == 200
    assert counts(db) == before
    assert db.query(models.UserCardSRS).filter_by(user_id=1, card_id=1).one().state == srs_before

    # Explicit changes to the shared demo learner need an account.
    for method, path, payload in (
        ("post", "/api/plan/replan", None),
        ("post", "/api/plan/items", {"title": "x", "plan_date": timeutil.local_today().isoformat(), "estimated_minutes": 5}),
        ("patch", "/api/roadmaps", {"title": "hacked"}),
        ("post", "/api/knowledge/lessons/1/notes", {"content": "x"}),
        ("post", "/api/knowledge/lessons/1/progress", {"event": "complete"}),
        ("post", "/api/flashcards", {"word": "synergy", "meaning": "x", "example_sentence": "y"}),
    ):
        assert getattr(client, method)(path, json=payload).status_code == 401, path


# --------------------------------------------------------------------------- blanks and the error log
def test_blank_answers_outside_exams_are_not_mistakes(client, seeded, db):
    result = client.post("/api/practice/submit", json={
        "answers": [{"question_id": seeded[108], "choice": "D"}, {"question_id": seeded[111], "choice": None}], "mode": "study",
    }).json()
    assert result["unanswered"] == 1 and result["errors_logged"] == 0
    assert db.query(models.ErrorLog).count() == 0


def test_blank_never_resets_an_existing_diagnosis(client, seeded, db):
    client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[108], "choice": "B"}], "mode": "study"})
    log = db.query(models.ErrorLog).filter_by(question_id=seeded[108]).one()
    log.review_stage, log.status = 2, "reviewed"
    db.commit()
    exam = client.post("/api/practice/submit", json={"answers": [{"question_id": seeded[108], "choice": None}], "mode": "exam"}).json()
    assert exam["errors_logged"] == 0
    db.expire_all()
    log = db.query(models.ErrorLog).filter_by(question_id=seeded[108]).one()
    assert (log.error_type, log.review_stage, log.status) == ("GRAMMAR", 2, "reviewed")


# --------------------------------------------------------------------------- SRS
def test_cram_reviews_do_not_reschedule_cards(client, seeded, db):
    client.post("/api/flashcards/1/review", json={"rating": 3})  # new card: first real review
    row = db.query(models.UserCardSRS).filter_by(user_id=1, card_id=1).one()
    first = (row.repetition_count, row.interval_days, row.next_review_at)
    for rating in (4, 4, 1):  # "Luyện toàn bộ" again the same evening
        assert client.post("/api/flashcards/1/review", json={"rating": rating}).status_code == 200
    db.expire_all()
    row = db.query(models.UserCardSRS).filter_by(user_id=1, card_id=1).one()
    assert (row.repetition_count, row.interval_days, row.next_review_at) == first
    assert db.query(models.SRSReviewLog).filter_by(card_id=1).count() == 1


def test_cards_due_later_today_count_as_due(client, seeded, db):
    today = timeutil.local_today() + timedelta(days=7)
    timeutil.set_now(timeutil.local_datetime_utc(today, 21, 0))
    client.post("/api/flashcards/1/review", json={"rating": 1})  # forgot at 21:00 -> back in 24h
    timeutil.set_now(timeutil.local_datetime_utc(today + timedelta(days=1), 8, 0))
    assert 1 in [card["card_id"] for card in client.get("/api/flashcards/due").json()]
    assert client.get("/api/flashcards/summary").json()["review_due"] >= 1


def test_parallel_srs_seeding_does_not_fail(seeded):
    with SessionLocal() as session:
        session.add(models.Flashcard(category="IT", word="deploy", meaning="triển khai", example_sentence="We deploy daily."))
        session.commit()
    errors = []

    def seed():
        try:
            with SessionLocal() as session:
                insights.ensure_srs_records(session, 1)
        except Exception as exc:  # pragma: no cover - the assertion below reports it
            errors.append(exc)

    threads = [threading.Thread(target=seed) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    with SessionLocal() as session:
        assert session.query(models.UserCardSRS).filter_by(user_id=1).count() == 6


# --------------------------------------------------------------------------- plan
def _planner_keys(db) -> list:
    db.expire_all()
    return [
        (i.plan_date, i.kind, i.lesson_number, i.part)
        for i in db.query(models.StudyPlanItem).filter_by(user_id=1, source="planner")
    ]


def test_parallel_first_loads_build_the_plan_once(seeded, db):
    errors = []

    def load():
        try:
            with SessionLocal() as session:
                planner.ensure_plan(session, 1)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=load) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    keys = _planner_keys(db)
    assert errors == [] and keys and len(keys) == len(set(keys))


def test_replan_keeps_work_already_started_today(client, seeded, db):
    client.patch("/api/learner/profile", json={"study_days": [0, 1, 2, 3, 4, 5, 6]})
    today = client.post("/api/plan/replan").json()["days"][0]["items"]
    practice = next(i for i in today if i["kind"] == "practice" and i["lesson_number"])
    questions = client.get("/api/tests/ETS2024_01/questions", params={"lesson": practice["lesson_number"]}).json()
    client.post("/api/practice/submit", json={"answers": [{"question_id": q["id"], "choice": q["correct_choice"]} for q in questions], "mode": "study"})

    after = client.post("/api/plan/replan").json()["days"][0]["items"]
    kept = next(i for i in after if i["id"] == practice["id"])
    assert kept["progress"] >= 1
    keys = [(i["kind"], i["lesson_number"], i["part"]) for i in after if i["source"] == "planner"]
    assert len(keys) == len(set(keys))


# --------------------------------------------------------------------------- curriculum
def test_listening_questions_are_not_grammar_lessons(db, seeded):
    question = db.query(models.TestQuestion).filter_by(part="Part 2").first()
    question.lesson_number = 2  # what the old ingest script stored
    db.add(models.QuestionAttempt(user_id=1, question_id=question.id, is_correct=False, part="Part 2", lesson_number=2))
    db.commit()
    assert curriculum.classify_question(question)["lesson_number"] is None
    assert maintenance.run(db)["listening_lessons"] == 2
    db.expire_all()
    assert db.query(models.TestQuestion).filter_by(part="Part 2").first().lesson_number is None
    assert db.query(models.QuestionAttempt).filter_by(part="Part 2").first().lesson_number is None


def test_guest_translation_is_not_saved_on_the_shared_card(client, seeded, db, production_mode, monkeypatch):
    from server.routers import flashcard_router

    async def fake_translate(sentence, keyword=None):
        return "Bản dịch thử"

    monkeypatch.setattr(flashcard_router, "translate_sentence_to_vi", fake_translate)
    shown = client.post("/api/flashcards/1/translate-example")
    assert shown.status_code == 200 and shown.json()["example_translation"] == "Bản dịch thử"
    db.expire_all()
    assert db.get(models.Flashcard, 1).example_translation is None


def test_parallel_forced_replans_do_not_duplicate_tasks(seeded, db):
    errors = []

    def replan():
        try:
            with SessionLocal() as session:
                planner.ensure_plan(session, 1, force=True)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=replan) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    keys = _planner_keys(db)
    assert errors == [] and keys and len(keys) == len(set(keys))
