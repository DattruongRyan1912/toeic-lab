"""Small in-memory sliding-window rate limiter (single uvicorn process, no extra dependency)."""
import ipaddress
import threading
import time
from collections import deque
from typing import Optional

from fastapi import HTTPException, Request

from server import config
from server.deps import get_token_from_request
from server.utils.security import decode_access_token

MAX_KEYS = 10_000  # keys come from user input (login identifiers): never let the table grow without bound

_lock = threading.Lock()
_hits: dict = {}  # (bucket, key) -> (deque of monotonic timestamps, window seconds)


def _parse(rule: str) -> tuple:
    limit, _, window = rule.partition("/")
    return max(1, int(limit)), max(1, int(window))


def _evict(now: float) -> None:
    """Drop keys whose window has passed; if still too many, drop the least recently used. Caller holds _lock."""
    for key in [k for k, (queue, window) in _hits.items() if not queue or queue[-1] <= now - window]:
        del _hits[key]
    if len(_hits) >= MAX_KEYS:
        by_last_hit = sorted(_hits, key=lambda k: _hits[k][0][-1])
        for key in by_last_hit[: len(_hits) - MAX_KEYS + 1]:
            del _hits[key]


def hit(bucket: str, key: str, rule: str) -> None:
    """Record one request for (bucket, key); raise 429 once the rule's quota is used up."""
    limit, window = _parse(rule)
    now = time.monotonic()
    with _lock:
        entry = _hits.get((bucket, key))
        if entry is None:
            if len(_hits) >= MAX_KEYS:
                _evict(now)
            entry = _hits[(bucket, key)] = (deque(), window)
        queue = entry[0]
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


# Loopback, RFC 1918 and unique-local ranges: where the BFF / reverse proxy / docker network connect from.
_INTERNAL_NETWORKS = tuple(
    ipaddress.ip_network(net) for net in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7")
)


def _is_internal(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in _INTERNAL_NETWORKS)


def client_ip(request: Request) -> str:
    """The caller's IP for per-IP limits.

    X-Forwarded-For is only trusted when the request reaches the API from an internal address (the Next.js
    BFF or a reverse proxy on the same host/network), and then only the entry appended by our own proxy:
    the TRUSTED_PROXY_HOPS-th address from the right. Anything a client writes into the header itself sits
    further left and is ignored, and direct requests from the internet use the socket address.
    """
    peer = request.client.host if request.client else "unknown"
    hops = config.TRUSTED_PROXY_HOPS
    if hops <= 0 or not _is_internal(peer):
        return peer
    chain = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    return chain[-hops] if len(chain) >= hops else peer


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
