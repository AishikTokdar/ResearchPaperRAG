from __future__ import annotations

import logging
from threading import Lock
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
INVALID_KEY_THRESHOLD = 2

_LOCK = Lock()
_MODEL_FAILURES: Dict[str, int] = {}
_INVALID_KEY_FAILURES: Dict[str, int] = {}


def is_auth_or_invalid_key_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    keywords = [
        "401",
        "unauthorized",
        "invalid_api_key",
        "invalid api key",
        "incorrect api key",
        "invalid key",
        "authentication",
        "auth_error",
        "invalid_token",
        "permission_denied",
    ]
    return any(kw in msg for kw in keywords)


def record_failure(model_id: str) -> None:
    if not model_id:
        return
    with _LOCK:
        _MODEL_FAILURES[model_id] = _MODEL_FAILURES.get(model_id, 0) + 1


def record_invalid_key_failure(provider_name: str, model_id: str) -> None:
    if not provider_name:
        return
    pname = provider_name.lower()
    with _LOCK:
        _INVALID_KEY_FAILURES[pname] = _INVALID_KEY_FAILURES.get(pname, 0) + 1
        if model_id:
            _MODEL_FAILURES[model_id] = _MODEL_FAILURES.get(model_id, 0) + 1


def record_success(provider_name: str, model_id: str) -> None:
    with _LOCK:
        if model_id in _MODEL_FAILURES:
            _MODEL_FAILURES[model_id] = 0
        if provider_name:
            pname = provider_name.lower()
            if pname in _INVALID_KEY_FAILURES:
                _INVALID_KEY_FAILURES[pname] = 0


def is_model_healthy(model_id: str) -> bool:
    if not model_id:
        return True
    with _LOCK:
        return _MODEL_FAILURES.get(model_id, 0) < MAX_CONSECUTIVE_FAILURES


def get_invalid_key_failure_count(provider_name: str) -> int:
    if not provider_name:
        return 0
    with _LOCK:
        return _INVALID_KEY_FAILURES.get(provider_name.lower(), 0)


def is_provider_invalid_key(provider_name: str) -> bool:
    return get_invalid_key_failure_count(provider_name) > INVALID_KEY_THRESHOLD


def get_provider_status(provider_name: str, has_credentials: bool, models: List[str]) -> str:
    if not has_credentials:
        return "api_key_not_set"

    if is_provider_invalid_key(provider_name):
        return "invalid_api_key"

    if not models:
        return "unavailable"

    healthy_count = sum(1 for m in models if is_model_healthy(m))
    total = len(models)

    if healthy_count == total:
        return "working"
    if healthy_count > 0:
        return "partial"
    return "unavailable"


def get_all_model_failures() -> Dict[str, int]:
    with _LOCK:
        return dict(_MODEL_FAILURES)


def reset_all_failures() -> None:
    with _LOCK:
        _MODEL_FAILURES.clear()
        _INVALID_KEY_FAILURES.clear()
