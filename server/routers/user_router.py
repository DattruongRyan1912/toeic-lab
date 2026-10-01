from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.schemas import UserRead, UserUpdate
from server.services import profile_service

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def get_me(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return profile_service.serialize(profile_service.get_user(db, user_id))


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    """Same rules as /api/learner/profile: exam date rescales the roadmap, planning inputs rebuild the plan."""
    user = profile_service.get_user(db, user_id)
    try:
        profile_service.apply(db, user, profile_service.normalize(payload.model_dump(exclude_unset=True)))
    except profile_service.ProfileError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.refresh(user)
    return profile_service.serialize(user)
