"""Idempotent data maintenance run at startup (after the additive schema migration)."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from server.models import ErrorLog, Roadmap, SprintTask, TestQuestion
from server.services import curriculum, error_log_service, practice_service

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
            elif log.topic:
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
        changed += 1
    return changed


def run(db: Session) -> dict:
    result = {
        "attempts": practice_service.backfill_attempts(db),
        "roadmaps": backfill_roadmaps(db),
        "error_logs": backfill_error_logs(db),
    }
    db.commit()
    if any(result.values()):
        logger.info("Maintenance backfill: %s", result)
    return result
