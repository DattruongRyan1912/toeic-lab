"""Study-time tracking.

Every learning event (an SRS card, a submitted quiz, a minute on a lesson page, a mentor question...)
is folded into StudySession rows: consecutive events of the same kind/ref within SESSION_GAP are merged,
so "minutes studied per day" is a simple sum. Callers commit.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from server.models import StudySession
from server.utils import timeutil

SESSION_GAP = timedelta(minutes=20)
MAX_EVENT_SECONDS = 3 * 3600
DEFAULT_CARD_SECONDS = 20
MAX_CARD_SECONDS = 120  # longer means the learner walked away
MENTOR_QUESTION_SECONDS = 30
KINDS = ("srs", "practice", "review", "lesson", "mentor", "listening", "reading", "other")


def track(
    db: Session,
    user_id: int,
    kind: str,
    seconds: float,
    *,
    items: int = 0,
    correct: int = 0,
    ref: Optional[str] = None,
    at: Optional[datetime] = None,
) -> StudySession:
    at = at or timeutil.utcnow()
    seconds = max(0, min(int(round(seconds or 0)), MAX_EVENT_SECONDS))
    query = db.query(StudySession).filter(StudySession.user_id == user_id, StudySession.kind == kind)
    query = query.filter(StudySession.ref == ref) if ref is not None else query.filter(StudySession.ref.is_(None))
    last = query.order_by(StudySession.last_activity_at.desc(), StudySession.id.desc()).first()
    if (
        last is not None
        and last.last_activity_at is not None
        and timedelta(0) <= at - last.last_activity_at <= SESSION_GAP + timedelta(seconds=seconds)
        and timeutil.local_date_of(last.started_at) == timeutil.local_date_of(at)
    ):
        last.duration_seconds = (last.duration_seconds or 0) + seconds
        last.items = (last.items or 0) + items
        last.correct = (last.correct or 0) + correct
        last.last_activity_at = at
        return last
    session = StudySession(
        user_id=user_id,
        kind=kind,
        ref=ref,
        started_at=at - timedelta(seconds=seconds),
        last_activity_at=at,
        duration_seconds=seconds,
        items=items,
        correct=correct,
    )
    # A session that would start "yesterday" (long event right after midnight) is pinned to today.
    if timeutil.local_date_of(session.started_at) != timeutil.local_date_of(at):
        session.started_at = timeutil.local_day_start_utc(timeutil.local_date_of(at))
    db.add(session)
    return session


def card_seconds(duration_ms: Optional[int]) -> int:
    if not duration_ms or duration_ms <= 0:
        return DEFAULT_CARD_SECONDS
    return min(MAX_CARD_SECONDS, max(1, round(duration_ms / 1000)))


def sessions_between(db: Session, user_id: int, start_day: date, end_day: date) -> list:
    """Sessions whose local start date is in [start_day, end_day)."""
    since = timeutil.local_day_start_utc(start_day)
    until = timeutil.local_day_start_utc(end_day)
    return (
        db.query(StudySession)
        .filter(StudySession.user_id == user_id, StudySession.started_at >= since, StudySession.started_at < until)
        .all()
    )


def seconds_by_day(db: Session, user_id: int, since_day: date, until_day: Optional[date] = None) -> dict:
    until_day = until_day or timeutil.local_today() + timedelta(days=1)
    totals: dict = defaultdict(int)
    for session in sessions_between(db, user_id, since_day, until_day):
        totals[timeutil.local_date_of(session.started_at)] += session.duration_seconds or 0
    return totals


def seconds_by_day_and_kind(db: Session, user_id: int, since_day: date, until_day: date) -> dict:
    """{(date, kind, ref): seconds} — used by the planner to detect completed lesson / listening items."""
    totals: dict = defaultdict(int)
    for session in sessions_between(db, user_id, since_day, until_day):
        totals[(timeutil.local_date_of(session.started_at), session.kind, session.ref)] += session.duration_seconds or 0
    return totals


def minutes_series(db: Session, user_id: int, days: int = 14, goal_minutes: int = 60) -> list:
    today = timeutil.local_today()
    start = today - timedelta(days=days - 1)
    per_kind: dict = defaultdict(lambda: defaultdict(int))
    for session in sessions_between(db, user_id, start, today + timedelta(days=1)):
        per_kind[timeutil.local_date_of(session.started_at)][session.kind] += session.duration_seconds or 0
    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        kinds = per_kind.get(day, {})
        total = sum(kinds.values())
        series.append(
            {
                "date": day,
                "minutes": round(total / 60),
                "goal_minutes": goal_minutes,
                "by_kind": {kind: round(value / 60, 1) for kind, value in sorted(kinds.items())},
            }
        )
    return series
