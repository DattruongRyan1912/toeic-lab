"""AI allowance and usage accounting.

* Every HTTP call to an AI provider is logged (who, which feature, provider/model, key alias, tokens, latency,
  outcome). Calls made for one learner action share a request id.
* Allowance: a learner gets AI_DAILY_QUOTA successful AI requests per local day plus the short burst limit
  (RATE_LIMIT_AI). Admins and accounts an admin marked unlimited are exempt from both; an account with a custom
  quota uses that number instead and skips the burst limit. Guests get AI_GUEST_DAILY_QUOTA requests per IP
  per 24 hours.
* Keys stay in .env. Admins can switch a key off by alias, and a key that answered 429/403 rests for
  AI_KEY_COOLDOWN_SECONDS so the next requests start with a healthy one.
"""
from __future__ import annotations

import contextvars
import logging
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from server import config
from server.database import SessionLocal
from server.deps import active_user_id, get_token_from_request, is_test_mode
from server.models import AIKeyState, AIUsageLog, User
from server.utils import rate_limit, timeutil

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- request context
@dataclass
class UsageContext:
    request_id: str
    user_id: Optional[int]
    endpoint: str
    client_ip: Optional[str] = None


_context: contextvars.ContextVar = contextvars.ContextVar("ai_usage_context", default=None)


def current() -> UsageContext:
    return _context.get() or UsageContext(uuid.uuid4().hex, None, "system")


# --------------------------------------------------------------------------- keys
def key_aliases() -> list:
    """[(alias, provider, key)] for every configured key, in .env order. Aliases are stable: gemini-1, gemini-2... (URL-safe)"""
    gemini = list(getattr(config, "GEMINI_API_KEYS", []))
    if config.GEMINI_API_KEY and config.GEMINI_API_KEY not in gemini:
        gemini.insert(0, config.GEMINI_API_KEY)
    keys = [(f"gemini-{i}", "gemini", key) for i, key in enumerate(gemini, start=1)]
    if config.DEEPSEEK_API_KEY:
        keys.append(("deepseek", "deepseek", config.DEEPSEEK_API_KEY))
    if config.OPENAI_API_KEY:
        keys.append(("openai", "openai", config.OPENAI_API_KEY))
    return keys


def alias_of(provider: str, key: str) -> Optional[str]:
    return next((alias for alias, name, value in key_aliases() if name == provider and value == key), None)


_state_lock = threading.Lock()
_cooling: dict = {}  # alias -> monotonic time until which the key rests
_disabled_cache: tuple = (0.0, frozenset())
_inflight_reservations: Counter = Counter()  # caller_key -> active in-flight count
_guest_success_counts: dict = {}  # (ip, local_date_str) -> ok count


def disabled_aliases() -> frozenset:
    global _disabled_cache
    loaded_at, aliases = _disabled_cache
    if time.monotonic() - loaded_at < 5:
        return aliases
    try:
        with SessionLocal() as db:
            aliases = frozenset(alias for (alias,) in db.query(AIKeyState.alias).filter(AIKeyState.disabled.is_(True)))
    except Exception:  # pragma: no cover - table missing before init_db
        aliases = frozenset()
    _disabled_cache = (time.monotonic(), aliases)
    return aliases


def forget_cached_states() -> None:
    global _disabled_cache
    _disabled_cache = (0.0, frozenset())


def cool_down(alias: Optional[str]) -> None:
    if alias and config.AI_KEY_COOLDOWN_SECONDS:
        with _state_lock:
            _cooling[alias] = time.monotonic() + config.AI_KEY_COOLDOWN_SECONDS


def cooling_seconds(alias: str) -> int:
    with _state_lock:
        until = _cooling.get(alias, 0.0)
    return max(0, round(until - time.monotonic()))


def reset() -> None:
    with _state_lock:
        _cooling.clear()
        _inflight_reservations.clear()
        _guest_success_counts.clear()
    forget_cached_states()


def order_keys(provider: str, keys: list) -> list:
    """Drop keys an admin switched off; keys resting after a 429 go last (still a fallback, never first)."""
    disabled = disabled_aliases()
    enabled = [key for key in keys if alias_of(provider, key) not in disabled]
    return [k for k in enabled if not cooling_seconds(alias_of(provider, k) or "")] + [
        k for k in enabled if cooling_seconds(alias_of(provider, k) or "")
    ]


# --------------------------------------------------------------------------- recording
def _tokens(provider: str, body: Optional[dict]) -> tuple:
    if not isinstance(body, dict):
        return None, None, None
    if provider == "gemini":
        meta = body.get("usageMetadata") or {}
        return meta.get("promptTokenCount"), meta.get("candidatesTokenCount"), meta.get("totalTokenCount")
    usage = body.get("usage") or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")


def record(
    provider: str,
    model: Optional[str],
    alias: Optional[str],
    status: str,
    *,
    http_status: Optional[int] = None,
    body: Optional[dict] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Log one provider call. Accounting must never break the learner's request."""
    ctx = current()
    prompt, completion, total = _tokens(provider, body)
    try:
        with SessionLocal() as db:
            db.add(AIUsageLog(
                request_id=ctx.request_id, user_id=ctx.user_id, endpoint=ctx.endpoint, provider=provider, model=model,
                key_alias=alias, status=status, http_status=http_status, prompt_tokens=prompt, completion_tokens=completion,
                total_tokens=total, latency_ms=latency_ms, error=(error or None) and error[:200], created_at=timeutil.utcnow(),
            ))
            db.commit()
        if status == "ok" and ctx.user_id is None and ctx.client_ip:
            today_str = timeutil.local_today().isoformat()
            with _state_lock:
                key = (ctx.client_ip, today_str)
                _guest_success_counts[key] = _guest_success_counts.get(key, 0) + 1
                if len(_guest_success_counts) > 10_000:
                    expired = [k for k in _guest_success_counts if k[1] != today_str]
                    for k in expired:
                        del _guest_success_counts[k]
    except Exception:  # pragma: no cover - logging only
        logger.warning("Could not record AI usage", exc_info=True)


# --------------------------------------------------------------------------- allowance
def _day_start():
    return timeutil.local_day_start_utc(timeutil.local_today())


def requests_today(db: Session, user_id: int) -> int:
    """Learner actions today that got at least one successful provider answer."""
    return (
        db.query(func.count(func.distinct(AIUsageLog.request_id)))
        .filter(AIUsageLog.user_id == user_id, AIUsageLog.status == "ok", AIUsageLog.created_at >= _day_start())
        .scalar()
        or 0
    )


def plan_of(user: Optional[User]) -> tuple:
    """(plan, daily quota or None for unlimited). plan: admin | unlimited | custom | default | guest."""
    if user is None:
        return "guest", config.AI_GUEST_DAILY_QUOTA
    if user.role == "admin":
        return "admin", None
    if user.ai_unlimited:
        return "unlimited", None
    if user.ai_daily_quota is not None:
        return "custom", max(0, user.ai_daily_quota)
    return "default", config.AI_DAILY_QUOTA


def allowance(db: Session, user: Optional[User], ip: Optional[str] = None) -> dict:
    plan, quota = plan_of(user)
    if user is not None:
        used = requests_today(db, user.id)
    elif ip:
        today_str = timeutil.local_today().isoformat()
        with _state_lock:
            used = _guest_success_counts.get((ip, today_str), 0)
    else:
        used = None
    return {
        "plan": plan,
        "unlimited": quota is None,
        "daily_quota": quota,
        "used_today": used,
        "remaining": None if quota is None or used is None else max(0, quota - used),
    }


def _seconds_to_midnight() -> int:
    tomorrow = timeutil.local_day_start_utc(timeutil.local_today() + timedelta(days=1))
    return max(1, int((tomorrow - timeutil.utcnow()).total_seconds()))


def _caller(request: Request, db: Session) -> Optional[User]:
    token = get_token_from_request(request.headers.get("authorization"), request.cookies.get("access_token"))
    if token:
        return db.get(User, active_user_id(token, db))
    if is_test_mode():  # tests act as the demo learner, like the other learner dependencies
        return db.get(User, config.DEFAULT_USER_ID)
    return None


def guard(endpoint: str):
    """Route dependency for AI features: checks the caller's allowance, reserves a slot, and tags provider calls for the log."""

    async def dependency(request: Request):
        with SessionLocal() as db:
            user = _caller(request, db)
            plan, quota = plan_of(user)
            ip = rate_limit.client_ip(request)
            caller_key = f"user:{user.id}" if user is not None else f"guest:{ip}"

            if plan == "guest":
                if quota is None or quota <= 0:
                    raise HTTPException(
                        status_code=429,
                        detail="Tính năng AI hiện chỉ dành cho tài khoản đã đăng nhập. Vui lòng đăng nhập để tiếp tục.",
                        headers={"Retry-After": str(_seconds_to_midnight())},
                    )
                rate_limit.hit("ai", f"ip:{ip}", config.RATE_LIMIT_AI)
                today_str = timeutil.local_today().isoformat()
                with _state_lock:
                    used = _guest_success_counts.get((ip, today_str), 0)
                    in_flight = _inflight_reservations.get(caller_key, 0)
                    if used + in_flight >= quota:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Khách chỉ dùng được {quota} lượt AI mỗi ngày. Đăng nhập để có thêm lượt.",
                            headers={"Retry-After": str(_seconds_to_midnight())},
                        )
                    _inflight_reservations[caller_key] += 1
            elif quota is not None:
                if plan == "default":
                    rate_limit.hit("ai", f"user:{user.id}", config.RATE_LIMIT_AI)
                with _state_lock:
                    used = requests_today(db, user.id)
                    in_flight = _inflight_reservations.get(caller_key, 0)
                    if used + in_flight >= quota:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Bạn đã dùng hết {quota} lượt AI hôm nay. Hạn mức làm mới lúc 0h; cần thêm hãy liên hệ quản trị viên.",
                            headers={"Retry-After": str(_seconds_to_midnight())},
                        )
                    _inflight_reservations[caller_key] += 1

        _context.set(
            UsageContext(
                uuid.uuid4().hex,
                user.id if user is not None else None,
                endpoint,
                client_ip=ip if plan == "guest" else None,
            )
        )
        try:
            yield
        finally:
            if quota is not None:
                with _state_lock:
                    if _inflight_reservations[caller_key] > 0:
                        _inflight_reservations[caller_key] -= 1
                        if _inflight_reservations[caller_key] == 0:
                            del _inflight_reservations[caller_key]

    return dependency


# --------------------------------------------------------------------------- admin reporting
def key_health(db: Session) -> list:
    since = timeutil.utcnow() - timedelta(hours=24)
    states = {s.alias: s for s in db.query(AIKeyState).all()}
    counts = Counter(
        (alias, status)
        for alias, status in db.query(AIUsageLog.key_alias, AIUsageLog.status).filter(AIUsageLog.created_at >= since)
    )
    rows = []
    for alias, provider, _key in key_aliases():
        last_ok = db.query(func.max(AIUsageLog.created_at)).filter(AIUsageLog.key_alias == alias, AIUsageLog.status == "ok").scalar()
        last_error = (
            db.query(AIUsageLog)
            .filter(AIUsageLog.key_alias == alias, AIUsageLog.status != "ok")
            .order_by(AIUsageLog.created_at.desc())
            .first()
        )
        state = states.get(alias)
        rows.append({
            "alias": alias,
            "provider": provider,
            "disabled": bool(state and state.disabled),
            "note": state.note if state else None,
            "cooling_seconds": cooling_seconds(alias),
            "ok_24h": counts[(alias, "ok")],
            "errors_24h": counts[(alias, "error")],
            "rate_limited_24h": counts[(alias, "rate_limited")],
            "last_ok_at": last_ok,
            "last_error_at": last_error.created_at if last_error else None,
            "last_error": (f"HTTP {last_error.http_status}: " if last_error and last_error.http_status else "") + (last_error.error or "") if last_error else None,
        })
    return rows


def overview(db: Session, days: int = 7) -> dict:
    today = timeutil.local_today()
    since = timeutil.local_day_start_utc(today - timedelta(days=days - 1))
    rows = (
        db.query(AIUsageLog.created_at, AIUsageLog.request_id, AIUsageLog.user_id, AIUsageLog.endpoint, AIUsageLog.status, AIUsageLog.total_tokens)
        .filter(AIUsageLog.created_at >= since)
        .all()
    )
    by_day = {today - timedelta(days=offset): {"requests": set(), "calls": 0, "tokens": 0, "errors": 0} for offset in range(days)}
    endpoints, users = defaultdict(set), defaultdict(lambda: {"requests": set(), "tokens": 0})
    for created_at, request_id, user_id, endpoint, status, tokens in rows:
        bucket = by_day.get(timeutil.local_date_of(created_at))
        if bucket is None:
            continue
        bucket["calls"] += 1
        bucket["tokens"] += tokens or 0
        if status == "ok":
            bucket["requests"].add(request_id)
            endpoints[endpoint].add(request_id)
            if user_id is not None:
                users[user_id]["requests"].add(request_id)
        else:
            bucket["errors"] += 1
        if user_id is not None:
            users[user_id]["tokens"] += tokens or 0
    names = {uid: name for uid, name in db.query(User.id, User.username).filter(User.id.in_(list(users)))} if users else {}
    top = sorted(users.items(), key=lambda item: (-len(item[1]["requests"]), -item[1]["tokens"]))[:10]
    daily = [
        {"date": day, "requests": len(b["requests"]), "calls": b["calls"], "tokens": b["tokens"], "errors": b["errors"]}
        for day, b in sorted(by_day.items())
    ]
    return {
        "today": daily[-1],
        "days": daily,
        "by_endpoint": sorted(({"endpoint": e, "requests": len(r)} for e, r in endpoints.items()), key=lambda x: -x["requests"]),
        "top_users": [
            {"user_id": uid, "username": names.get(uid, f"#{uid}"), "requests": len(data["requests"]), "tokens": data["tokens"]}
            for uid, data in top
        ],
        "keys": key_health(db),
        "limits": {
            "daily_quota": config.AI_DAILY_QUOTA,
            "guest_daily_quota": config.AI_GUEST_DAILY_QUOTA,
            "burst": config.RATE_LIMIT_AI,
            "key_cooldown_seconds": config.AI_KEY_COOLDOWN_SECONDS,
            "retention_days": config.AI_USAGE_RETENTION_DAYS,
        },
    }


def set_key_disabled(db: Session, alias: str, disabled: bool, note: Optional[str] = None) -> None:
    if alias not in {a for a, _, _ in key_aliases()}:
        raise LookupError(f"Không có key '{alias}' trong cấu hình")
    state = db.get(AIKeyState, alias) or AIKeyState(alias=alias)
    state.disabled = disabled
    state.note = note
    state.updated_at = timeutil.utcnow()
    db.add(state)
    db.commit()
    forget_cached_states()


def purge_old_logs(db: Session) -> int:
    cutoff = timeutil.utcnow() - timedelta(days=config.AI_USAGE_RETENTION_DAYS)
    return db.query(AIUsageLog).filter(AIUsageLog.created_at < cutoff).delete(synchronize_session=False)
