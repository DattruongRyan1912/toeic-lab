from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.models import Roadmap, SprintTask
from server.schemas import RoadmapRead, RoadmapUpdate, SprintTaskRead, SprintTaskUpdate
from server.services import insights, planner, skills
from server.utils.timeutil import utcnow

router = APIRouter(prefix="/api/roadmaps", tags=["Roadmaps"])


def _require_roadmap(db: Session, user_id: int) -> Roadmap:
    roadmap = insights.get_roadmap(db, user_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Chưa có lộ trình. Hãy chạy scripts/seed_database.py")
    return roadmap


def _read(db: Session, user_id: int, roadmap: Roadmap) -> dict:
    user = insights.get_or_create_user(db, user_id)
    report = skills.compute(db, user_id)
    evidence = planner.milestone_evidence(db, user_id, roadmap, report, skills.predict_score(report, user))
    return insights.serialize_roadmap(roadmap, evidence)


@router.get("", response_model=RoadmapRead)
def get_user_roadmap(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return _read(db, user_id, _require_roadmap(db, user_id))


@router.patch("", response_model=RoadmapRead)
def update_user_roadmap(payload: RoadmapUpdate, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    roadmap = _require_roadmap(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if "start_date" in changes:
        roadmap.start_date = changes["start_date"]
    if changes.get("title"):
        roadmap.title = changes["title"].strip()
    planner.rescale_roadmap(db, insights.get_or_create_user(db, user_id))
    db.commit()
    if "start_date" in changes:
        planner.ensure_plan(db, user_id, force=True)
    db.refresh(roadmap)
    return _read(db, user_id, roadmap)


@router.patch("/tasks/{task_id}", response_model=SprintTaskRead)
def toggle_sprint_task(
    task_id: int,
    payload: SprintTaskUpdate,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    task = (
        db.query(SprintTask)
        .join(Roadmap, Roadmap.id == SprintTask.roadmap_id)
        .filter(SprintTask.id == task_id, Roadmap.user_id == user_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = payload.is_completed
    task.completed_at = utcnow() if payload.is_completed else None
    db.commit()
    db.refresh(task)
    return task
