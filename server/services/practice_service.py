"""Practice: grading, attempt tracking, spaced review of mistakes and personalized question sets.

submit() is the single path for every answered question (mock tests, lesson drills, error reviews,
smart sets): it records a QuestionAttempt per answer (with time), creates/reschedules error logs,
advances the review schedule of mistakes answered correctly, tracks study time and refreshes gaps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from server.models import ErrorLog, QuestionAttempt, TestQuestion, UserTestSubmission
from server.services import activity, curriculum, error_log_service, insights, scoring
from server.utils import timeutil

MODES = ("practice", "study", "exam", "review", "smart")
MAX_QUESTION_MS = 15 * 60 * 1000


class PracticeError(ValueError):
    pass


@dataclass
class Answer:
    question_id: int
    choice: Optional[str] = None
    time_ms: Optional[int] = None


def _root_cause(question: TestQuestion, choice: Optional[str]) -> str:
    if not choice:
        return "Bỏ trống (hết giờ hoặc chưa kịp làm). Luyện chiến thuật phân bổ thời gian."
    analysis = (question.distractor_analysis or "").strip()
    return f"Chọn ({choice}) thay vì ({question.correct_choice}). {analysis}".strip()


def submit(
    db: Session,
    user_id: int,
    answers: list,
    *,
    mode: str = "practice",
    part: Optional[str] = None,
    lesson_number: Optional[int] = None,
    time_spent_seconds: int = 0,
    log_errors: bool = True,
    test_id: Optional[str] = None,
    persist: bool = True,
) -> dict:
    """Grade answers; with persist=False (guests) nothing is written and the demo learner is untouched."""
    if persist:
        insights.get_or_create_user(db, user_id)
    mode = mode if mode in MODES else "practice"
    by_id: dict = {}
    for answer in answers:
        by_id[int(answer.question_id)] = answer  # last answer per question wins
    if not by_id:
        raise PracticeError("Bài nộp không có câu hỏi nào")
    if len(by_id) > 200:
        raise PracticeError("Tối đa 200 câu mỗi lần nộp")
    query = db.query(TestQuestion).filter(TestQuestion.id.in_(by_id.keys()))
    if test_id:
        query = query.filter(TestQuestion.test_id == test_id)
    questions = query.order_by(TestQuestion.test_id.asc(), TestQuestion.question_no.asc()).all()
    if len(questions) != len(by_id):
        raise PracticeError("Có câu hỏi không thuộc đề này" if test_id else "Có câu hỏi không tồn tại")

    now = timeutil.utcnow()
    logs = (
        db.query(ErrorLog)
        .filter(ErrorLog.user_id == user_id, ErrorLog.question_id.in_(by_id.keys()))
        .order_by(ErrorLog.id.asc())
        .all()
        if persist
        else []
    )
    logged_questions = {log.question_id for log in logs}
    open_errors = {log.question_id: log for log in logs if log.status != "mastered"}

    results, stored, attempts, section_counts = [], [], [], {}
    logs_to_link = []
    reviews_advanced = errors_mastered = 0
    for question in questions:
        answer = by_id[question.id]
        choice = error_log_service.normalize_choice(answer.choice)
        time_ms = int(answer.time_ms) if answer.time_ms else None
        if time_ms is not None:
            time_ms = max(0, min(time_ms, MAX_QUESTION_MS))
        is_correct = choice is not None and choice == question.correct_choice
        cls = curriculum.classify_question(question)
        section = scoring.section_for_part(question.part)
        if section:
            correct, total = section_counts.get(section, (0, 0))
            section_counts[section] = (correct + int(is_correct), total + 1)
        error_type = "TIME" if choice is None else cls["error_type"]

        review_outcome = None
        if is_correct and question.id in open_errors:
            review_outcome = error_log_service.record_review(open_errors[question.id], correct=True, now=now)
            reviews_advanced += review_outcome in ("advanced", "mastered")
            errors_mastered += review_outcome == "mastered"

        result = {
            "question_id": question.id,
            "question_no": question.question_no,
            "test_id": question.test_id,
            "part": question.part,
            "user_choice": choice,
            "correct_choice": question.correct_choice,
            "is_correct": is_correct,
            "error_type": error_type,
            "trap_tag": cls["trap_tag"],
            "lesson_number": cls["lesson_number"],
            "error_log_id": open_errors[question.id].id if question.id in open_errors else None,
            "time_ms": time_ms,
            "review_outcome": review_outcome,
        }
        results.append(result)
        stored.append({k: result[k] for k in ("question_id", "question_no", "user_choice", "correct_choice", "is_correct", "time_ms")})
        attempts.append(
            QuestionAttempt(
                user_id=user_id,
                question_id=question.id,
                choice=choice,
                is_correct=is_correct,
                time_ms=time_ms,
                mode=mode,
                part=question.part,
                lesson_number=cls["lesson_number"],
                error_type=error_type,
                created_at=now,
            )
        )
        # A blank only says "not answered": outside exam mode it is not a mistake, and it never
        # overwrites the diagnosis of a question the learner already has in the error log.
        blank_is_mistake = mode == "exam" and question.id not in logged_questions
        if not is_correct and log_errors and persist and (choice is not None or blank_is_mistake):
            fields = {"user_choice": choice, "error_type": error_type, "root_cause": _root_cause(question, choice), "source": "mock_test"}
            error_log_service.enrich_from_question(fields, question)
            log, status = error_log_service.upsert_error_log(db, user_id, fields, dedupe=True)
            if status != "created":
                result["review_outcome"] = "reset"
            logs_to_link.append((result, log))

    correct_count = sum(1 for r in results if r["is_correct"])
    total = len(results)
    measured = [r["time_ms"] for r in results if r["time_ms"]]
    if not time_spent_seconds and measured:
        time_spent_seconds = round(sum(measured) / 1000)
    scaled = {
        section: value
        for section, (c, n) in section_counts.items()
        if (value := scoring.estimate_section_scaled(section, c, n)) is not None
    }
    tests = {q.test_id for q in questions}
    parts = {q.part for q in questions}
    summary = {
        "submission_id": None,
        "test_id": next(iter(tests)) if len(tests) == 1 else "MIXED",
        "part": part or (next(iter(parts)) if len(parts) == 1 else "Mixed"),
        "mode": mode,
        "lesson_number": lesson_number,
        "correct_count": correct_count,
        "total_questions": total,
        "unanswered": sum(1 for r in results if r["user_choice"] is None),
        "accuracy": round(correct_count / total, 4) if total else 0.0,
        "scaled_listening": scaled.get("listening"),
        "scaled_reading": scaled.get("reading"),
        "errors_logged": len(logs_to_link),
        "reviews_advanced": reviews_advanced,
        "errors_mastered": errors_mastered,
        "avg_time_seconds": round(sum(measured) / len(measured) / 1000, 1) if measured else None,
        "time_spent_seconds": time_spent_seconds,
        "results": results,
        "learning_gaps": [],
    }
    if not persist:
        return summary
    submission = UserTestSubmission(
        user_id=user_id,
        test_id=summary["test_id"],
        part=summary["part"],
        mode=mode,
        lesson_number=lesson_number,
        correct_count=correct_count,
        total_questions=total,
        answers_json=json.dumps(stored, ensure_ascii=False),
        raw_listening=section_counts.get("listening", (0, 0))[0],
        raw_reading=section_counts.get("reading", (0, 0))[0],
        scaled_listening=scaled.get("listening") or 0,
        scaled_reading=scaled.get("reading") or 0,
        total_scaled_score=(scaled["listening"] + scaled["reading"]) if len(scaled) == 2 else 0,
        time_spent_seconds=time_spent_seconds,
        submitted_at=now,
    )
    db.add(submission)
    db.flush()
    for attempt in attempts:
        attempt.submission_id = submission.id
        db.add(attempt)
    activity.track(
        db, user_id, "review" if mode == "review" else "practice", time_spent_seconds,
        items=total, correct=correct_count, ref=f"submission:{submission.id}", at=now,
    )
    db.commit()
    for result, log in logs_to_link:
        result["error_log_id"] = log.id
    insights.recompute_learning_gaps(db, user_id)

    return {**summary, "submission_id": submission.id, "learning_gaps": insights.open_gaps(db, user_id)}


# --------------------------------------------------------------------------- personalized sets
def review_queue(db: Session, user_id: int, limit: int = 20) -> list:
    """Questions behind error logs that are due for review: [(question, error_log)]."""
    logs = error_log_service.due_reviews(db, user_id)
    questions = {q.id: q for q in db.query(TestQuestion).filter(TestQuestion.id.in_([l.question_id for l in logs]))} if logs else {}
    pairs, seen = [], set()
    for log in logs:
        question = questions.get(log.question_id)
        if question is None or question.id in seen:
            continue
        seen.add(question.id)
        pairs.append((question, log))
        if len(pairs) >= limit:
            break
    return pairs


def _last_results(db: Session, user_id: int) -> dict:
    """question_id -> (is_correct, created_at) of the latest attempt."""
    latest = {}
    for question_id, is_correct, created_at in (
        db.query(QuestionAttempt.question_id, QuestionAttempt.is_correct, QuestionAttempt.created_at)
        .filter(QuestionAttempt.user_id == user_id)
        .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
    ):
        latest[question_id] = (bool(is_correct), created_at)
    return latest


def classify_difficulty(question: TestQuestion) -> str:
    """Classify question difficulty into 'easy', 'medium', or 'hard' based on part, position, and syntax lesson."""
    part = question.part or ""
    qno = question.question_no or 0
    lesson = question.lesson_number
    if not lesson and question.distractor_analysis:
        trap = curriculum.classify_trap(curriculum.extract_trap_tag(question.distractor_analysis), part)
        lesson = trap.lesson_number

    # Complex syntax patterns (Participles, Subjunctive, Inversion, Comparisons, Collocations)
    if lesson in (8, 9, 10, 11, 12):
        return "hard"

    if part == "Part 1":
        return "easy" if qno <= 4 else "medium"
    elif part == "Part 2":
        if qno <= 15:
            return "easy"
        elif qno <= 25:
            return "medium"
        return "hard"
    elif part in ("Part 3", "Part 4"):
        return "medium" if (qno % 3 != 0) else "hard"
    elif part in ("Part 5", "Part 6"):
        if lesson in (1, 5, 7):
            return "easy"
        if qno <= 110:
            return "easy"
        elif qno <= 124:
            return "medium"
        return "hard"
    elif part == "Part 7":
        return "medium" if qno <= 160 else "hard"

    return "medium"


def smart_set(db: Session, user_id: int, count: int = 10, report=None, difficulty: Optional[str] = None) -> list:
    """A personalized practice set: [(question, reason, difficulty)].

    Order of preference: mistakes due for review, unanswered/failed questions of the weakest lessons,
    questions never seen, then the questions answered longest ago (spaced practice).
    Adaptively matches difficulty based on learner mastery or requested difficulty level.
    """
    from server.services import skills  # local import: skills imports insights

    count = max(1, min(int(count), 50))
    report = report or skills.compute(db, user_id)
    chosen, picked = [], set()

    observed_masteries = [s.mastery for s in report.lessons.values() if s.attempts > 0]
    avg_mastery = sum(observed_masteries) / len(observed_masteries) if observed_masteries else 0.5

    def matches_diff(q: TestQuestion) -> bool:
        diff = classify_difficulty(q)
        if difficulty:
            return diff == difficulty
        if avg_mastery < 0.50:
            return diff in ("easy", "medium")
        elif avg_mastery >= 0.75:
            return diff in ("medium", "hard")
        return True

    def take(question, reason, strict: bool = False):
        if question.id in picked or len(chosen) >= count:
            return False
        diff = classify_difficulty(question)
        if strict and not matches_diff(question):
            return False
        picked.add(question.id)
        chosen.append((question, reason, diff))
        return True

    questions = db.query(TestQuestion).order_by(TestQuestion.test_id.asc(), TestQuestion.question_no.asc()).all()
    latest = _last_results(db, user_id)
    by_lesson: dict = {}
    for question in questions:
        lesson = curriculum.classify_question(question)["lesson_number"]
        by_lesson.setdefault(lesson, []).append(question)

    recent_cutoff = timeutil.utcnow() - timedelta(days=2)
    weak = sorted(
        (s for s in report.lessons.values() if s.question_count and s.status != "strong"),
        key=lambda s: (s.mastery, -s.open_errors),
    )

    # Pass 1: Questions strictly matching target/requested difficulty
    for question, log in review_queue(db, user_id, limit=max(1, count * 4 // 10)):
        take(question, f"Ôn lại câu sai (lần {min((log.review_stage or 0) + 1, 3)}/3)", strict=True)

    for stat in weak[:4]:
        for question in by_lesson.get(stat.lesson_number, []):
            last = latest.get(question.id)
            if last is None or (not last[0] and last[1] and last[1] < recent_cutoff):
                take(question, f"Chuyên đề cần củng cố: {stat.label} ({skills.percent(stat.mastery)})", strict=True)
            if len(chosen) >= count * 8 // 10:
                break

    for question in questions:
        if question.id not in latest:
            take(question, "Câu mới chưa làm", strict=True)

    for question in sorted((q for q in questions if q.id in latest), key=lambda q: latest[q.id][1] or recent_cutoff):
        take(question, "Ôn tập ngắt quãng (làm lâu nhất)", strict=True)

    # Pass 2: Fallback if bank does not have enough questions of requested difficulty
    if len(chosen) < count:
        for question, log in review_queue(db, user_id, limit=max(1, count * 4 // 10)):
            take(question, f"Ôn lại câu sai (lần {min((log.review_stage or 0) + 1, 3)}/3)", strict=False)
        for stat in weak[:4]:
            for question in by_lesson.get(stat.lesson_number, []):
                last = latest.get(question.id)
                if last is None or (not last[0] and last[1] and last[1] < recent_cutoff):
                    take(question, f"Chuyên đề cần củng cố: {stat.label} ({skills.percent(stat.mastery)})", strict=False)
        for question in questions:
            if question.id not in latest:
                take(question, "Câu mới chưa làm", strict=False)
        for question in sorted((q for q in questions if q.id in latest), key=lambda q: latest[q.id][1] or recent_cutoff):
            take(question, "Ôn tập ngắt quãng (làm lâu nhất)", strict=False)

    return chosen


def backfill_attempts(db: Session) -> int:
    """One-off: older submissions only stored answers_json; turn them into QuestionAttempt rows."""
    if db.query(QuestionAttempt.id).first() is not None:
        return 0
    created = 0
    questions = {q.id: q for q in db.query(TestQuestion).all()}
    for submission in db.query(UserTestSubmission).filter(UserTestSubmission.answers_json.isnot(None)):
        try:
            items = json.loads(submission.answers_json)
        except (TypeError, ValueError):
            continue
        for item in items if isinstance(items, list) else []:
            question = questions.get(item.get("question_id")) if isinstance(item, dict) else None
            if question is None:
                continue
            cls = curriculum.classify_question(question)
            db.add(
                QuestionAttempt(
                    user_id=submission.user_id,
                    question_id=question.id,
                    submission_id=submission.id,
                    choice=item.get("user_choice"),
                    is_correct=bool(item.get("is_correct")),
                    mode=submission.mode or "practice",
                    part=question.part,
                    lesson_number=cls["lesson_number"],
                    error_type=cls["error_type"],
                    created_at=submission.submitted_at,
                )
            )
            created += 1
    if created:
        db.commit()
    return created
