"""Time helpers shared by models, services and routers.

Storage convention: every DateTime column holds *naive UTC*.
Presentation convention: "today", streaks, study plans and reminders use the learner's timezone
(APP_TIMEZONE, default Asia/Ho_Chi_Minh) so a review at 06:30 local time is not counted on the previous UTC day.

Every module reads the clock through utcnow(); tests and simulations can freeze or advance it.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from functools import lru_cache
from typing import Iterator, Optional

from server import config

_frozen_utc: Optional[datetime] = None


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def utcnow() -> datetime:
    """Naive UTC timestamp (replacement for the deprecated datetime.utcnow)."""
    if _frozen_utc is not None:
        return _frozen_utc
    return datetime.now(timezone.utc).replace(tzinfo=None)


def set_now(value: Optional[datetime]) -> None:
    """Freeze the clock at `value` (aware or naive UTC). None restores the real clock."""
    global _frozen_utc
    _frozen_utc = _naive_utc(value) if value is not None else None


def advance(**delta) -> datetime:
    """Move the clock forward, e.g. advance(days=1). Freezes at the current time first if needed."""
    set_now(utcnow() + timedelta(**delta))
    return utcnow()


@contextmanager
def frozen(value: datetime) -> Iterator[None]:
    previous = _frozen_utc
    set_now(value)
    try:
        yield
    finally:
        set_now(previous)


@lru_cache(maxsize=1)
def app_tz() -> tzinfo:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(config.APP_TIMEZONE)
    except Exception:  # tz database missing (slim images without tzdata) -> fixed offset fallback
        return timezone(timedelta(hours=7), "UTC+07")


def to_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(app_tz())


def local_now() -> datetime:
    return to_local(utcnow())


def local_today() -> date:
    return local_now().date()


def local_date_of(value: Optional[datetime]) -> Optional[date]:
    return to_local(value).date() if value else None


def local_day_start_utc(day: date) -> datetime:
    """Naive-UTC instant at which `day` starts in the learner's timezone."""
    start_local = datetime.combine(day, time.min, tzinfo=app_tz())
    return start_local.astimezone(timezone.utc).replace(tzinfo=None)


def local_datetime_utc(day: date, hour: int = 0, minute: int = 0) -> datetime:
    """Naive-UTC instant of a local wall-clock time (scheduling, tests)."""
    local = datetime.combine(day, time(hour, minute), tzinfo=app_tz())
    return local.astimezone(timezone.utc).replace(tzinfo=None)
