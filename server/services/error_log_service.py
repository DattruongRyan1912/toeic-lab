"""Error-log writes shared by the REST router, practice submissions and the AI mentor tools.

Every open error with a question in the bank is also a spaced-review item:
stage 0 is due one day after the mistake; a correct re-answer when due moves it to stage 1 (+3 days),
stage 2 (+7 days) and finally "mastered". A wrong re-answer resets it to stage 0.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from server.models import ErrorLog, TestQuestion
from server.services import curriculum
from server.utils import timeutil

_CHOICE_RE = re.compile(r"(?<![A-Za-z])([A-Da-d])(?![A-Za-z])")

REVIEW_INTERVAL_DAYS = {0: 1, 1: 3, 2: 7}
MASTERED_STAGE = 3


def normalize_choice(value) -> Optional[str]:
    """"B", "(b)", "(B) unanimous" -> "B"; anything else -> None."""
    if value is None:
        return None
    match = _CHOICE_RE.search(str(value).strip())
    return match.group(1).upper() if match else None


def find_question(db: Session, test_id: Optional[str], question_no: Optional[int]) -> Optional[TestQuestion]:
    if not test_id or not question_no:
        return None
    return db.query(TestQuestion).filter_by(test_id=test_id, question_no=question_no).first()


def enrich_from_question(fields: dict, question: Optional[TestQuestion]) -> dict:
    """Question-bank facts always win over user/LLM-provided values (no hallucinated answers)."""
    if question is None:
        if not fields.get("lesson_number") and fields.get("topic"):
            fields["lesson_number"] = curriculum.classify_trap(fields["topic"], fields.get("part")).lesson_number
        return fields
    cls = curriculum.classify_question(question)
    fields.update(
        test_id=question.test_id,
        part=question.part,
        question_no=question.question_no,
        question_id=question.id,
        correct_choice=question.correct_choice,
        question_content=fields.get("question_content") or question.sentence,
        topic=fields.get("topic") or cls["trap_tag"],
        lesson_number=cls["lesson_number"],
    )
    if not fields.get("key_rule_or_paraphrase"):
        fields["key_rule_or_paraphrase"] = question.paraphrase_pair
    if not fields.get("error_type"):
        fields["error_type"] = cls["error_type"]
    return fields


# --------------------------------------------------------------------------- spaced review of mistakes
def schedule_new(log: ErrorLog, now: Optional[datetime] = None) -> None:
    now = now or timeutil.utcnow()
    log.review_stage = 0
    log.next_review_at = now + timedelta(days=REVIEW_INTERVAL_DAYS[0])


def is_review_due(log: ErrorLog, now: Optional[datetime] = None) -> bool:
    """Due on (or after) the local calendar day of next_review_at."""
    if log.status == "mastered":
        return False
    if log.next_review_at is None:
        return True
    now = now or timeutil.utcnow()
    return timeutil.local_date_of(now) >= timeutil.local_date_of(log.next_review_at)


def record_review(log: ErrorLog, correct: bool, now: Optional[datetime] = None) -> str:
    """Apply one re-answer of the question behind `log`.

    Returns "advanced", "mastered", "reset" or "early" (correct but not due yet: nothing changes).
    """
    now = now or timeutil.utcnow()
    if not correct:
        log.review_stage = 0
        log.next_review_at = now + timedelta(days=REVIEW_INTERVAL_DAYS[0])
        log.status = "unresolved"
        log.last_reviewed_at = now
        return "reset"
    if log.status == "mastered" or not is_review_due(log, now):
        return "early"
    stage = (log.review_stage or 0) + 1
    log.review_stage = stage
    log.last_reviewed_at = now
    log.review_count = (log.review_count or 0) + 1
    if stage >= MASTERED_STAGE:
        log.status = "mastered"
        log.next_review_at = None
        return "mastered"
    log.status = "reviewed"
    log.next_review_at = now + timedelta(days=REVIEW_INTERVAL_DAYS[stage])
    return "advanced"


def apply_status(log: ErrorLog, status: str, now: Optional[datetime] = None) -> None:
    """Manual status change from the learner (or an agent tool) keeps the review schedule consistent."""
    now = now or timeutil.utcnow()
    if status == log.status:
        return
    if status in ("reviewed", "mastered"):
        log.review_count = (log.review_count or 0) + 1
        log.last_reviewed_at = now  # a manual review counts as a review (weekly report, history)
    if status == "mastered":
        log.review_stage = MASTERED_STAGE
        log.next_review_at = None
    elif status == "reviewed":
        log.review_stage = max(1, log.review_stage or 0)
        log.next_review_at = now + timedelta(days=REVIEW_INTERVAL_DAYS[min(log.review_stage, 2)])
    else:  # unresolved
        schedule_new(log, now)
    log.status = status


def open_filter():
    return or_(ErrorLog.status.is_(None), ErrorLog.status != "mastered")


def due_reviews(db: Session, user_id: int, limit: Optional[int] = None, now: Optional[datetime] = None) -> list:
    """Open, question-linked errors whose review is due today (oldest first)."""
    now = now or timeutil.utcnow()
    end_of_today = timeutil.local_day_start_utc(timeutil.local_date_of(now) + timedelta(days=1))
    query = (
        db.query(ErrorLog)
        .filter(
            ErrorLog.user_id == user_id,
            ErrorLog.question_id.isnot(None),
            open_filter(),
            or_(ErrorLog.next_review_at.is_(None), ErrorLog.next_review_at < end_of_today),
        )
        .order_by(ErrorLog.next_review_at.asc(), ErrorLog.id.asc())
    )
    return query.limit(limit).all() if limit else query.all()


def upsert_error_log(db: Session, user_id: int, fields: dict, *, dedupe: bool) -> tuple:
    """Create an error log, or — for automated sources — reuse the learner's log for the same question.

    Returns (ErrorLog, status) with status in {"created", "updated", "reopened"}.
    A repeated mistake resets the spaced-review schedule. Does not commit.
    """
    question_id = fields.get("question_id")
    now = timeutil.utcnow()
    if dedupe and question_id:
        existing = (
            db.query(ErrorLog)
            .filter_by(user_id=user_id, question_id=question_id)
            .order_by(ErrorLog.id.desc())
            .first()
        )
        if existing is not None:
            status = "reopened" if existing.status == "mastered" else "updated"
            record_review(existing, correct=False, now=now)
            existing.user_choice = fields.get("user_choice") or existing.user_choice
            if existing.source != "manual":  # never overwrite an analysis the learner wrote by hand
                existing.error_type = fields.get("error_type") or existing.error_type
                existing.root_cause = fields.get("root_cause") or existing.root_cause
                existing.key_rule_or_paraphrase = fields.get("key_rule_or_paraphrase") or existing.key_rule_or_paraphrase
            existing.topic = existing.topic or fields.get("topic")
            existing.lesson_number = existing.lesson_number or fields.get("lesson_number")
            return existing, status

    log = ErrorLog(
        user_id=user_id,
        test_id=fields.get("test_id") or "Practice",
        part=fields.get("part") or "Part 5",
        question_no=fields.get("question_no"),
        question_id=question_id,
        error_type=(fields.get("error_type") or "TRAP").upper(),
        user_choice=fields.get("user_choice"),
        correct_choice=fields.get("correct_choice"),
        question_content=fields.get("question_content"),
        image_url=fields.get("image_url"),
        root_cause=fields.get("root_cause") or "Chưa ghi nguyên nhân gốc",
        key_rule_or_paraphrase=fields.get("key_rule_or_paraphrase"),
        topic=fields.get("topic"),
        lesson_number=fields.get("lesson_number"),
        source=fields.get("source") or "manual",
        status="unresolved",
    )
    schedule_new(log, now)
    db.add(log)
    db.flush()
    return log, "created"
