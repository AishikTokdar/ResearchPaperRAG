"""
Per-client-IP sliding-window rate limits for expensive routes.

Mitigates abuse such as spamming new X-Chat-Session-Id values to fill the LRU
or hammering PDF indexing. Each limit is per client IP (not one global cap for
the server). Limits are in-memory (per API process); combine with a reverse
proxy for defense in depth when running multiple workers.

Implementation sketch: each key keeps a deque of monotonic timestamps; before
allowing a new hit, timestamps older than 60s are dropped, then length is
compared to the configured max — classic sliding window counter.
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from ..config import get_settings

_lock = threading.Lock()
_upload_hits: dict[str, deque[float]] = {}
_ask_hits: dict[str, deque[float]] = {}


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        trusted = any(
            ipaddress.ip_address(peer) in ipaddress.ip_network(cidr.strip(), strict=False)
            for cidr in get_settings().trusted_proxy_ips.split(",")
            if cidr.strip()
        )
    except ValueError:
        trusted = False
    x_real = request.headers.get("x-real-ip")
    if trusted and x_real:
        try:
            return str(ipaddress.ip_address(x_real.strip()))
        except ValueError:
            pass
    return peer


def _prune_and_allow(
    store: dict[str, deque[float]],
    key: str,
    max_events: int,
    window_seconds: float,
) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        if len(store) >= 10000:
            for stale_key in [k for k, hits in store.items() if not hits or hits[-1] < cutoff]:
                del store[stale_key]
            if key not in store and len(store) >= 10000:
                return False
        q = store.get(key)
        if q is None:
            q = deque()
            store[key] = q
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= max_events:
            return False
        q.append(now)
        return True


def check_upload_rate_limit(request: Request) -> None:
    settings = get_settings()
    n = int(settings.rate_limit_upload_per_minute)
    if n <= 0:
        return
    ip = client_ip(request)
    if not _prune_and_allow(_upload_hits, ip, n, 60.0):
        raise HTTPException(
            status_code=429,
            detail="Too many uploads from this address. Try again in a minute.",
            headers={"Retry-After": "60"},
        )


def check_ask_rate_limit(request: Request) -> None:
    settings = get_settings()
    n = int(settings.rate_limit_ask_per_minute)
    if n <= 0:
        return
    ip = client_ip(request)
    if not _prune_and_allow(_ask_hits, ip, n, 60.0):
        raise HTTPException(
            status_code=429,
            detail="Too many questions from this address. Try again in a minute.",
            headers={"Retry-After": "60"},
        )
