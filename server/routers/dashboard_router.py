from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from server.database import get_db
from server.models import (
    User, Roadmap, SprintTask, Flashcard, UserCardSRS, ErrorLog, AILearningGap
)
from server.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(user_id: int = 1, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    target_score = user.target_score if user else 800

    # Roadmap progress
    total_tasks = db.query(SprintTask).count()
    completed_tasks = db.query(SprintTask).filter_by(is_completed=True).count()
    roadmap_percent = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # SRS counts
    now = datetime.now(timezone.utc)
    # SQLite naive comparison fallback
    srs_due_count = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.next_review_at <= datetime.utcnow()
    ).count()

    srs_mastered_count = db.query(UserCardSRS).filter(
        UserCardSRS.user_id == user_id,
        UserCardSRS.state == "mastered"
    ).count()

    total_flashcards = db.query(Flashcard).count()

    # Error log RCA distribution
    errors = db.query(ErrorLog).filter_by(user_id=user_id).all()
    rca_counts = Counter(e.error_type for e in errors)
    # Ensure all 5 categories exist
    for rca in ["VOCAB", "GRAMMAR", "PHONETICS", "TRAP", "TIME"]:
        rca_counts.setdefault(rca, 0)

    # Top learning gaps
    gaps = db.query(AILearningGap).filter_by(user_id=user_id, is_resolved=False).limit(3).all()
    top_gaps = [g.topic for g in gaps] if gaps else ["Bẫy Similar Sound Part 2", "Rút gọn mệnh đề Part 5"]

    return DashboardStats(
        target_score=target_score,
        roadmap_percent=roadmap_percent,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        srs_due_count=srs_due_count,
        srs_mastered_count=srs_mastered_count,
        total_flashcards=total_flashcards,
        total_errors=len(errors),
        rca_breakdown=dict(rca_counts),
        top_learning_gaps=top_gaps
    )
