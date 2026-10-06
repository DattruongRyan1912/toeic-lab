from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id, require_learner_user_id
from server.models import StudyReminder
from server.schemas import StudyReminderCreate, StudyReminderRead, StudyReminderUpdate

router = APIRouter(prefix="/api/reminders", tags=["Study Reminders"])


def _get_owned(db: Session, reminder_id: int, user_id: int) -> StudyReminder:
    reminder = db.query(StudyReminder).filter_by(id=reminder_id, user_id=user_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.get("", response_model=List[StudyReminderRead])
def list_reminders(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return db.query(StudyReminder).filter_by(user_id=user_id).order_by(StudyReminder.scheduled_time.asc()).all()


@router.post("", response_model=StudyReminderRead, status_code=201)
def create_reminder(payload: StudyReminderCreate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    reminder = StudyReminder(user_id=user_id, is_active=True, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}", response_model=StudyReminderRead)
def update_reminder(
    reminder_id: int,
    payload: StudyReminderUpdate,
    user_id: int = Depends(require_learner_user_id),
    db: Session = Depends(get_db),
):
    reminder = _get_owned(db, reminder_id, user_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(reminder, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}")
def delete_reminder(reminder_id: int, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    db.delete(_get_owned(db, reminder_id, user_id))
    db.commit()
    return {"status": "deleted", "id": reminder_id}
