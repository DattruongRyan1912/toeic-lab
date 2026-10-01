from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.schemas import PracticeQuestion, PracticeSubmitRequest, QuizSubmitResult
from server.services import practice_service
from server.routers.test_router import serialize_question

router = APIRouter(prefix="/api/practice", tags=["Practice (personalized)"])


@router.post("/submit", response_model=QuizSubmitResult)
def submit_practice(payload: PracticeSubmitRequest, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    answers = [practice_service.Answer(a.question_id, a.choice, a.time_ms) for a in payload.answers]
    try:
        return practice_service.submit(
            db, user_id, answers, mode=payload.mode, part=payload.part, lesson_number=payload.lesson_number,
            time_spent_seconds=payload.time_spent_seconds, log_errors=payload.log_errors,
        )
    except practice_service.PracticeError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/review-queue", response_model=List[PracticeQuestion])
def review_queue(
    limit: int = Query(20, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Mistakes whose spaced review (1-3-7 days) is due today."""
    return [
        {
            **serialize_question(question),
            "reason": f"Ôn lại lần {min((log.review_stage or 0) + 1, 3)}/3",
            "error_log_id": log.id,
            "review_stage": log.review_stage or 0,
            "difficulty": practice_service.classify_difficulty(question),
        }
        for question, log in practice_service.review_queue(db, user_id, limit)
    ]


@router.get("/smart", response_model=List[PracticeQuestion])
def smart_set(
    count: int = Query(10, ge=1, le=50),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Personalized set: due mistakes, weakest lessons, unseen questions, then spaced practice."""
    return [
        {**serialize_question(question), "reason": reason, "difficulty": diff}
        for question, reason, diff in practice_service.smart_set(db, user_id, count, difficulty=difficulty)
    ]
