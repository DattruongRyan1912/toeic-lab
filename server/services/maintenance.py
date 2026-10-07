"""Idempotent data maintenance run at startup (after the additive schema migration)."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from server.database import SessionLocal
from server.models import ErrorLog, Flashcard, QuestionAttempt, Roadmap, SprintTask, TestQuestion
from server.services import ai_usage, curriculum, error_log_service, practice_service

logger = logging.getLogger(__name__)


def backfill_roadmaps(db: Session) -> int:
    changed = 0
    for roadmap in db.query(Roadmap).filter(Roadmap.base_total_weeks.is_(None)):
        roadmap.base_total_weeks = roadmap.total_weeks or 24
        changed += 1
    for task in db.query(SprintTask).filter(SprintTask.base_week.is_(None)):
        task.base_week = task.week_number
        task.source = task.source or "seed"
        changed += 1
    return changed


def backfill_error_logs(db: Session) -> int:
    """Older error logs: derive lesson_number and give open ones a review schedule."""
    changed = 0
    questions = {q.id: q for q in db.query(TestQuestion).all()}
    for log in db.query(ErrorLog).filter((ErrorLog.lesson_number.is_(None)) | (ErrorLog.review_stage.is_(None))):
        if log.lesson_number is None:
            question = questions.get(log.question_id) if log.question_id else None
            if question is not None:
                log.lesson_number = curriculum.classify_question(question)["lesson_number"]
            elif log.topic and log.part not in curriculum.LISTENING_PARTS:
                log.lesson_number = curriculum.classify_trap(log.topic, log.part).lesson_number
        if log.review_stage is None:
            if log.status == "mastered":
                log.review_stage = error_log_service.MASTERED_STAGE
            elif log.status == "reviewed":
                log.review_stage = 1
                log.next_review_at = log.next_review_at or log.created_at
            else:
                log.review_stage = 0
                log.next_review_at = log.next_review_at or log.created_at
        changed += db.is_modified(log)
    return changed


def detach_listening_from_lessons(db: Session) -> int:
    """Lessons 01-12 are Part 5/6 grammar: listening rows linked to them skewed lesson mastery and advice."""
    changed = 0
    for model in (TestQuestion, QuestionAttempt, ErrorLog):
        changed += (
            db.query(model)
            .filter(model.part.in_(curriculum.LISTENING_PARTS), model.lesson_number.isnot(None))
            .update({model.lesson_number: None}, synchronize_session=False)
        )
    return changed


def clear_failed_translations(db: Session) -> int:
    """Older versions saved the 'translation unavailable' message as a card's translation."""
    return (
        db.query(Flashcard)
        .filter(Flashcard.example_translation == "Bản dịch tự động tạm thời chưa khả dụng.")
        .update({Flashcard.example_translation: None}, synchronize_session=False)
    )


def run(db: Session) -> dict:
    result = {
        "listening_lessons": detach_listening_from_lessons(db),
        "failed_translations": clear_failed_translations(db),
        "old_ai_usage_logs": ai_usage.purge_old_logs(db),
        "attempts": practice_service.backfill_attempts(db),
        "roadmaps": backfill_roadmaps(db),
        "error_logs": backfill_error_logs(db),
    }
    db.commit()
    if any(result.values()):
        logger.info("Maintenance backfill: %s", result)
    return result


async def maintenance_loop(stop: asyncio.Event, interval_seconds: int = 3600) -> None:
    """Periodic maintenance loop that purges expired logs. Runs hourly."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
        if stop.is_set():
            break
        try:
            with SessionLocal() as db:
                purged = ai_usage.purge_old_logs(db)
                if purged:
                    logger.info("Periodic maintenance: purged %d expired AI usage logs", purged)
        except Exception:
            logger.exception("Periodic maintenance task encountered an error")
