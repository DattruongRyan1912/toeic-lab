"""Optional Telegram dispatcher for StudyReminder rows.

Runs as a background task inside the API process only when TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID are set. Each active reminder fires at most once per local day, within
GRACE_MINUTES after its scheduled time (so a restart shortly after 21:00 still delivers it).
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

from server import config
from server.database import SessionLocal
from server.models import ErrorLog, StudyReminder
from server.utils import timeutil

logger = logging.getLogger(__name__)

GRACE_MINUTES = 60
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


WEEKLY_REPORT = "weekly_report"
WEEKLY_REPORT_WEEKDAY = 6  # Sunday (Mon=0), sent at the reminder's time


def telegram_configured() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)


def dispatch_enabled() -> bool:
    return config.REMINDER_DISPATCH_ENABLED and telegram_configured()


def is_due(reminder: StudyReminder, now_local: datetime) -> bool:
    if not reminder.is_active:
        return False
    match = HHMM_RE.match(reminder.scheduled_time or "")
    if not match:
        return False
    scheduled = now_local.replace(hour=int(match.group(1)), minute=int(match.group(2)), second=0, microsecond=0)
    if not scheduled <= now_local < scheduled + timedelta(minutes=GRACE_MINUTES):
        return False
    if reminder.reminder_type == WEEKLY_REPORT and now_local.weekday() != WEEKLY_REPORT_WEEKDAY:
        return False
    return timeutil.local_date_of(reminder.last_triggered_at) != now_local.date()


def compose_message(db, reminder: StudyReminder) -> str:
    from server.services import error_log_service, insights, planner, weekly_report  # keep module import light

    if reminder.reminder_type == WEEKLY_REPORT:
        report = weekly_report.build(db, reminder.user_id)
        return f"{reminder.message}\n\n{weekly_report.to_markdown(report)}".replace("*", "")  # plain text for Telegram

    srs = insights.srs_counts(db, reminder.user_id)
    due_errors = len(error_log_service.due_reviews(db, reminder.user_id))
    open_errors = db.query(ErrorLog).filter(ErrorLog.user_id == reminder.user_id, ErrorLog.status != "mastered").count()
    planner.ensure_plan(db, reminder.user_id)  # the learner may not have opened the app today
    pending = [i for i in planner.items_for_day(db, reminder.user_id) if i["status"] == "pending"]
    lines = [f"⏰ {reminder.message}", ""]
    if pending:
        lines.append(f"🗓️ Kế hoạch hôm nay còn {len(pending)} nhiệm vụ (~{sum(i['estimated_minutes'] for i in pending)} phút):")
        lines += [f"• {i['title']}" for i in pending[:4]]
    lines.append(f"📌 {srs['session_size']} thẻ SRS cần ôn • {due_errors} câu sai đến hạn ôn • {open_errors} câu sai chưa khắc phục.")
    return "\n".join(lines)


async def send_telegram(text: str) -> bool:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text})
    if response.status_code != 200:
        logger.warning("Telegram sendMessage failed with HTTP %s", response.status_code)
    return response.status_code == 200


async def dispatch_due_reminders(now_local: Optional[datetime] = None) -> int:
    now_local = now_local or timeutil.local_now()
    sent = 0
    with SessionLocal() as db:
        for reminder in db.query(StudyReminder).filter(StudyReminder.is_active.is_(True)).all():
            if not is_due(reminder, now_local):
                continue
            if await send_telegram(compose_message(db, reminder)):
                reminder.last_triggered_at = timeutil.utcnow()
                db.commit()
                sent += 1
    return sent


async def reminder_loop(stop: asyncio.Event, interval_seconds: int = 30) -> None:
    while not stop.is_set():
        try:
            await dispatch_due_reminders()
        except Exception:
            logger.exception("Reminder dispatch failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
