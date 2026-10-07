from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id, optional_learner_id, require_learner_user_id
from server.models import LearnerMemory
from server.schemas import (
    ActivityPing,
    LearnerMemoryCreate,
    LearnerMemoryRead,
    LearnerMemoryUpdate,
    OnboardingRequest,
    Suggestion,
    UserRead,
    UserUpdate,
)
from server.services import activity, ai_agent_service, coach, insights, planner, profile_service, skills, weekly_report
from server.utils import timeutil

router = APIRouter(prefix="/api/learner", tags=["Learner (personalization)"])


def _apply_profile(db: Session, user_id: int, changes: dict) -> dict:
    user = profile_service.get_user(db, user_id)
    try:
        profile_service.apply(db, user, profile_service.normalize(changes))
    except profile_service.ProfileError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.refresh(user)
    return profile_service.serialize(user)


@router.get("/profile", response_model=UserRead)
def get_profile(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return profile_service.serialize(profile_service.get_user(db, user_id))


@router.patch("/profile", response_model=UserRead)
def update_profile(payload: UserUpdate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    return _apply_profile(db, user_id, payload.model_dump(exclude_unset=True))


@router.post("/onboarding")
def onboarding(payload: OnboardingRequest, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    """First-run personalization: profile + baseline + schedule; self-reported weaknesses become AI memories."""
    data = payload.model_dump(exclude={"weak_areas"})
    user = profile_service.get_user(db, user_id)
    try:
        changes = profile_service.normalize({k: v for k, v in data.items() if v is not None})
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    profile_service.apply(db, user, changes, replan=False)
    if payload.weak_areas and payload.weak_areas.strip():
        text = payload.weak_areas.strip()
        exists = db.query(LearnerMemory).filter_by(user_id=user_id, content=text).first()
        if exists is None:
            db.add(LearnerMemory(user_id=user_id, category="struggle", content=f"Tự nhận điểm yếu: {text}", source="onboarding", pinned=True))
    user.onboarded_at = user.onboarded_at or timeutil.utcnow()
    planner.rescale_roadmap(db, user)
    db.commit()
    planner.ensure_plan(db, user_id, force=True)
    db.refresh(user)
    return {"profile": profile_service.serialize(user), "plan": planner.week_view(db, user_id)}


@router.get("/insights")
def learner_insights(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    """Everything the learner's history says: mastery per lesson/part, prediction, pace, SRS quality, study time."""
    user = profile_service.get_user(db, user_id)
    report = skills.compute(db, user_id)
    return {
        "lessons": [s.as_dict() for s in report.lessons.values()],
        "parts": [s.as_dict() for s in report.parts.values()],
        "sections": {key: s.as_dict() for key, s in report.sections.items()},
        "prediction": skills.predict_score(report, user),
        "pace": skills.pace_summary(report),
        "srs_retention": skills.srs_retention(db, user_id),
        "leech_cards": skills.leech_cards(db, user_id),
        "study_minutes": activity.minutes_series(db, user_id, days=14, goal_minutes=user.daily_goal_minutes or 60),
        "focus": planner.week_view(db, user_id, report=report)["focus"],
        "total_attempts": report.total_attempts,
        "priors": report.priors,
    }


@router.get("/weekly-report")
def get_weekly_report(
    end: Optional[date] = Query(None, description="Ngày cuối của tuần (mặc định hôm nay)"),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Last 7 days: study time, accuracy vs the week before, mastery changes, mistakes, SRS, plan completion."""
    if end and end > timeutil.local_today():
        raise HTTPException(status_code=422, detail="Ngày kết thúc không được ở tương lai")
    report = weekly_report.build(db, user_id, end)
    report["markdown"] = weekly_report.to_markdown(report)
    return report


@router.get("/suggestions", response_model=List[Suggestion])
def learner_suggestions(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    online = not ai_agent_service.provider_status()["offline"]
    return coach.suggestions(db, user_id, ai_online=online)


@router.post("/activity")
def track_activity(payload: ActivityPing, user_id: Optional[int] = Depends(optional_learner_id), db: Session = Depends(get_db)):
    """Heartbeat for time spent outside graded activities (lesson pages, listening drills with the in-app timer)."""
    if user_id is None:
        return {"status": "ignored", "session_id": None, "duration_seconds": 0}  # guests: nothing is stored
    insights.get_or_create_user(db, user_id)
    session = activity.track(db, user_id, payload.kind, payload.seconds, ref=payload.ref)
    db.commit()
    return {"status": "tracked", "session_id": session.id, "duration_seconds": session.duration_seconds}


# --------------------------------------------------------------------------- memories
def _owned_memory(db: Session, memory_id: int, user_id: int) -> LearnerMemory:
    memory = db.query(LearnerMemory).filter_by(id=memory_id, user_id=user_id).first()
    if memory is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi nhớ")
    return memory


@router.get("/memories", response_model=List[LearnerMemoryRead])
def list_memories(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return (
        db.query(LearnerMemory)
        .filter_by(user_id=user_id)
        .order_by(LearnerMemory.pinned.desc(), LearnerMemory.updated_at.desc(), LearnerMemory.id.desc())
        .all()
    )


@router.post("/memories", response_model=LearnerMemoryRead, status_code=201)
def create_memory(payload: LearnerMemoryCreate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    insights.get_or_create_user(db, user_id)
    memory = LearnerMemory(user_id=user_id, category=payload.category, content=payload.content.strip(), pinned=payload.pinned, source="user")
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.patch("/memories/{memory_id}", response_model=LearnerMemoryRead)
def update_memory(memory_id: int, payload: LearnerMemoryUpdate, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    memory = _owned_memory(db, memory_id, user_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(memory, key, value.strip() if isinstance(value, str) else value)
    memory.updated_at = timeutil.utcnow()
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/memories/{memory_id}")
def delete_memory(memory_id: int, user_id: int = Depends(require_learner_user_id), db: Session = Depends(get_db)):
    db.delete(_owned_memory(db, memory_id, user_id))
    db.commit()
    return {"status": "deleted", "id": memory_id}
