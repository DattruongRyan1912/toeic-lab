from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import Flashcard, UserCardSRS
from server.schemas import FlashcardRead, UserCardSRSRead, SRSReviewRequest
from server.services.srs_service import calculate_sm2_review

router = APIRouter(prefix="/api/flashcards", tags=["Flashcards & SRS"])

@router.get("", response_model=List[FlashcardRead])
def list_flashcards(
    category: str = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    query = db.query(Flashcard)
    if category:
        query = query.filter_by(category=category)
    return query.limit(limit).all()

@router.get("/due", response_model=List[UserCardSRSRead])
def get_due_srs_cards(
    user_id: int = 1,
    limit: int = Query(30),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    # Query cards that are due for review
    due_records = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.next_review_at <= now
    ).order_by(UserCardSRS.next_review_at.asc()).limit(limit).all()

    # If no cards strictly due, fallback to returning active learning cards or newest
    if not due_records:
        due_records = db.query(UserCardSRS).filter(
            UserCardSRS.user_id == user_id
        ).order_by(UserCardSRS.last_reviewed_at.asc().nullsfirst()).limit(limit).all()

    return due_records

@router.post("/{card_id}/review", response_model=UserCardSRSRead)
def submit_srs_review(
    card_id: int,
    payload: SRSReviewRequest,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    srs = db.query(UserCardSRS).filter_by(user_id=user_id, card_id=card_id).first()
    if not srs:
        # Create SRS record if missing
        srs = UserCardSRS(user_id=user_id, card_id=card_id)
        db.add(srs)
        db.commit()
        db.refresh(srs)

    # Compute next SM-2 interval
    rep, ease, interval, state, next_date = calculate_sm2_review(
        current_repetition=srs.repetition_count,
        current_ease=srs.ease_factor,
        current_interval=srs.interval_days,
        rating=payload.rating
    )

    srs.repetition_count = rep
    srs.ease_factor = ease
    srs.interval_days = interval
    srs.state = state
    srs.next_review_at = next_date.replace(tzinfo=None)
    srs.last_reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(srs)
    return srs
