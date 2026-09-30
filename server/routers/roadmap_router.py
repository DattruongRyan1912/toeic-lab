from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from server.database import get_db
from server.models import Roadmap, SprintTask
from server.schemas import RoadmapRead, SprintTaskRead, SprintTaskUpdate

router = APIRouter(prefix="/api/roadmaps", tags=["Roadmaps"])

@router.get("", response_model=RoadmapRead)
def get_user_roadmap(user_id: int = 1, db: Session = Depends(get_db)):
    roadmap = db.query(Roadmap).filter_by(user_id=user_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap

@router.patch("/tasks/{task_id}", response_model=SprintTaskRead)
def toggle_sprint_task(task_id: int, payload: SprintTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(SprintTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = payload.is_completed
    task.completed_at = datetime.utcnow() if payload.is_completed else None
    db.commit()
    db.refresh(task)
    return task
