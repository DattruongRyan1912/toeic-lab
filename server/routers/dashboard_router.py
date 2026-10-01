from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.database import get_db
from server.deps import current_user_id
from server.schemas import DashboardStats
from server.services import insights

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return insights.build_dashboard(db, user_id)
