from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.models import StudyPlanItem
from server.schemas import PlanItemCreate, PlanItemRead, PlanItemUpdate
from server.services import insights, planner
from server.utils import timeutil

router = APIRouter(prefix="/api/plan", tags=["Adaptive plan"])


def _owned(db: Session, item_id: int, user_id: int) -> StudyPlanItem:
    item = db.query(StudyPlanItem).filter_by(id=item_id, user_id=user_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
    return item


def _read(db: Session, user_id: int, item: StudyPlanItem) -> dict:
    progress = planner.derive_progress(db, user_id, [item])
    return planner.serialize_item(item, progress.get(item.id))


@router.get("/week")
def get_week(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    """Rolling 7-day plan (regenerated once a day from the latest learning data)."""
    return planner.week_view(db, user_id)


@router.post("/replan")
def replan(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    insights.get_or_create_user(db, user_id)
    planner.ensure_plan(db, user_id, force=True)
    return planner.week_view(db, user_id)


@router.post("/items", response_model=PlanItemRead, status_code=201)
def add_item(payload: PlanItemCreate, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    today = timeutil.local_today()
    if payload.plan_date < today:
        raise HTTPException(status_code=422, detail="Không thể thêm nhiệm vụ vào ngày đã qua")
    insights.get_or_create_user(db, user_id)
    item = StudyPlanItem(
        user_id=user_id, plan_date=payload.plan_date, kind="custom", title=payload.title.strip(), detail=payload.detail,
        estimated_minutes=payload.estimated_minutes, lesson_number=payload.lesson_number, status="pending", source="user", sort_order=50,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _read(db, user_id, item)


@router.patch("/items/{item_id}", response_model=PlanItemRead)
def update_item(item_id: int, payload: PlanItemUpdate, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    item = _owned(db, item_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status"):
        item.status = changes["status"]
        item.completed_at = timeutil.utcnow() if item.status == "done" else None
    if changes.get("plan_date"):
        item.plan_date = changes["plan_date"]
        if item.source == "planner":
            item.source = "user"  # a moved item is the learner's decision: keep it when replanning
    if changes.get("title"):
        item.title = changes["title"].strip()
    db.commit()
    db.refresh(item)
    return _read(db, user_id, item)


@router.delete("/items/{item_id}")
def delete_item(item_id: int, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    item = _owned(db, item_id, user_id)
    if item.source == "planner":
        item.status = "skipped"  # planner items come back on replan; skipping keeps the decision
        db.commit()
        return {"status": "skipped", "id": item_id}
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": item_id}
