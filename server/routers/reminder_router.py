from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import StudyReminder
from server.schemas import StudyReminderRead, StudyReminderUpdate

router = APIRouter(prefix="/api/reminders", tags=["Study Reminders"])

@router.get("", response_model=List[StudyReminderRead])
def list_reminders(user_id: int = 1, db: Session = Depends(get_db)):
    return db.query(StudyReminder).filter_by(user_id=user_id).all()

@router.patch("/{reminder_id}", response_model=StudyReminderRead)
def update_reminder(
    reminder_id: int,
    payload: StudyReminderUpdate,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    rem = db.query(StudyReminder).filter_by(id=reminder_id, user_id=user_id).first()
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if payload.scheduled_time is not None:
        rem.scheduled_time = payload.scheduled_time
    if payload.message is not None:
        rem.message = payload.message
    if payload.is_active is not None:
        rem.is_active = payload.is_active

    db.commit()
    db.refresh(rem)
    return rem
