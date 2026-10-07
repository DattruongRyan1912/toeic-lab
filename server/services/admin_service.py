"""Admin console: user listing with learning stats, account lock and role changes."""
from datetime import timedelta
from typing import Optional

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from server.models import ErrorLog, QuestionAttempt, SRSReviewLog, StudySession, User, UserTestSubmission
from server.utils.timeutil import utcnow

ROLES = ("learner", "admin")


class AdminError(ValueError):
    pass


def _stats_query(db: Session):
    """Users joined with per-user aggregates; one query, no N+1."""
    week_ago = utcnow() - timedelta(days=7)
    sessions = (
        db.query(
            StudySession.user_id.label("user_id"),
            func.max(StudySession.last_activity_at).label("last_active_at"),
            func.coalesce(func.sum(StudySession.duration_seconds), 0).label("study_seconds"),
            func.coalesce(
                func.sum(case((StudySession.started_at >= week_ago, StudySession.duration_seconds), else_=0)), 0
            ).label("study_seconds_7d"),
        )
        .group_by(StudySession.user_id)
        .subquery()
    )
    attempts = (
        db.query(
            QuestionAttempt.user_id.label("user_id"),
            func.count(QuestionAttempt.id).label("attempts"),
            func.coalesce(func.sum(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)), 0).label("correct"),
        )
        .group_by(QuestionAttempt.user_id)
        .subquery()
    )
    query = (
        db.query(
            User,
            sessions.c.last_active_at,
            func.coalesce(sessions.c.study_seconds, 0),
            func.coalesce(sessions.c.study_seconds_7d, 0),
            func.coalesce(attempts.c.attempts, 0),
            func.coalesce(attempts.c.correct, 0),
        )
        .outerjoin(sessions, sessions.c.user_id == User.id)
        .outerjoin(attempts, attempts.c.user_id == User.id)
    )
    return query


def _row(user: User, last_active_at, study_seconds, study_seconds_7d, attempts, correct) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name or user.username,
        "role": user.role or "learner",
        "is_active": user.is_active is not False,
        "has_password": bool(user.hashed_password),
        "target_score": user.target_score or 800,
        "onboarded": user.onboarded_at is not None,
        "created_at": user.created_at,
        "last_active_at": last_active_at,
        "study_minutes_total": round(study_seconds / 60),
        "study_minutes_7d": round(study_seconds_7d / 60),
        "attempts": attempts,
        "accuracy": round(correct / attempts, 3) if attempts else None,
    }


def summary(db: Session) -> dict:
    week_ago = utcnow() - timedelta(days=7)
    return {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "admins": db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0,
        "locked": db.query(func.count(User.id)).filter(User.is_active.is_(False)).scalar() or 0,
        "active_7d": db.query(func.count(func.distinct(StudySession.user_id)))
        .filter(StudySession.last_activity_at >= week_ago)
        .scalar()
        or 0,
    }


def list_users(
    db: Session,
    q: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = _stats_query(db)
    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(User.username).like(pattern),
                func.lower(User.email).like(pattern),
                func.lower(User.display_name).like(pattern),
            )
        )
    if role in ROLES:
        query = query.filter(User.role == role) if role == "admin" else query.filter(or_(User.role.is_(None), User.role != "admin"))
    if status == "locked":
        query = query.filter(User.is_active.is_(False))
    elif status == "active":
        query = query.filter(or_(User.is_active.is_(None), User.is_active.is_(True)))
    total = query.count()
    rows = query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit).all()
    return {"summary": summary(db), "total": total, "items": [_row(*row) for row in rows]}


def get_user_detail(db: Session, user_id: int) -> dict:
    query = _stats_query(db)
    row = query.filter(User.id == user_id).first()
    if row is None:
        raise LookupError("Không tìm thấy người dùng")
    user = row[0]
    recent = (
        db.query(UserTestSubmission)
        .filter(UserTestSubmission.user_id == user_id)
        .order_by(UserTestSubmission.submitted_at.desc())
        .limit(5)
        .all()
    )
    return {
        **_row(*row),
        "headline": user.headline,
        "exam_date": user.exam_date,
        "daily_goal_minutes": user.daily_goal_minutes,
        "submissions": db.query(func.count(UserTestSubmission.id)).filter(UserTestSubmission.user_id == user_id).scalar() or 0,
        "srs_reviews": db.query(func.count(SRSReviewLog.id)).filter(SRSReviewLog.user_id == user_id).scalar() or 0,
        "open_errors": db.query(func.count(ErrorLog.id))
        .filter(ErrorLog.user_id == user_id, ErrorLog.status != "mastered")
        .scalar()
        or 0,
        "recent_submissions": [
            {
                "id": s.id,
                "test_id": s.test_id,
                "part": s.part,
                "mode": s.mode,
                "correct_count": s.correct_count,
                "total_questions": s.total_questions,
                "total_scaled_score": s.total_scaled_score,
                "submitted_at": s.submitted_at,
            }
            for s in recent
        ],
    }


def update_user(db: Session, actor: User, user_id: int, role: Optional[str], is_active: Optional[bool]) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise LookupError("Không tìm thấy người dùng")
    # Self-changes are refused, which also guarantees at least one active admin always remains.
    if user.id == actor.id:
        raise AdminError("Không thể tự đổi quyền hoặc tự khoá tài khoản của chính mình")
    if role is not None:
        if role not in ROLES:
            raise AdminError(f"Role không hợp lệ: {role}")
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    return get_user_detail(db, user_id)
