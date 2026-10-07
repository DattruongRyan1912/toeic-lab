"""Small in-memory sliding-window rate limiter (single uvicorn process, no extra dependency)."""
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request

from server import config
from server.deps import get_token_from_request
from server.utils.security import decode_access_token

_lock = threading.Lock()
_hits: dict = defaultdict(deque)


def _parse(rule: str) -> tuple:
    limit, _, window = rule.partition("/")
    return max(1, int(limit)), max(1, int(window))


def hit(bucket: str, key: str, rule: str) -> None:
    """Record one request for (bucket, key); raise 429 once the rule's quota is used up."""
    limit, window = _parse(rule)
    now = time.monotonic()
    with _lock:
        queue = _hits[(bucket, key)]
        while queue and queue[0] <= now - window:
            queue.popleft()
        if len(queue) >= limit:
            retry_after = int(queue[0] + window - now) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Bạn thao tác quá nhanh, vui lòng thử lại sau {retry_after} giây.",
                headers={"Retry-After": str(retry_after)},
            )
        queue.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()


def client_ip(request: Request) -> str:
    # The Next.js BFF forwards X-Forwarded-For from the reverse proxy; fall back to the socket peer.
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    return first or (request.client.host if request.client else "unknown")


def _caller_key(request: Request) -> str:
    token: Optional[str] = get_token_from_request(request.headers.get("authorization"), request.cookies.get("access_token"))
    if token:
        try:
            return f"user:{decode_access_token(token)['sub']}"
        except Exception:
            pass
    return f"ip:{client_ip(request)}"


def limit_register(request: Request) -> None:
    hit("register", client_ip(request), config.RATE_LIMIT_REGISTER)


def limit_ai(request: Request) -> None:
    """Dependency for endpoints that call an LLM: protects the provider quota."""
    hit("ai", _caller_key(request), config.RATE_LIMIT_AI)
