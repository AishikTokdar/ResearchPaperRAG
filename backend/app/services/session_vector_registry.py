"""
Per-browser anonymous session vector stores (LRU-bounded).

Each X-Chat-Session-Id (UUID) gets its own FAISS persist directory so concurrent
demo users do not overwrite each other's indexes. Oldest sessions are evicted
when max_sessions is exceeded.

VPS / scaling: disk paths are shared across processes. For correct writes, prefer
a single API worker per instance (or sticky sessions to the same worker), or
you can get concurrent upload races to the same session folder from different workers.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import OrderedDict

from .vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# UUID v4 (case-insensitive)
_SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_session_id(session_id: str) -> bool:
    return bool(_SESSION_ID_RE.match(session_id.strip()))


class SessionVectorRegistry:
    """
    In-process registry: maps browser ``session_id`` -> ``VectorStoreService``.

    ``OrderedDict`` + ``move_to_end`` implements LRU: when at capacity, the
    least-recently-used session is dropped from the registry and idle disk state is removed.
    In-flight readers retain their immutable index reference.
    """

    def __init__(self, max_sessions: int) -> None:
        self._max = max(4, min(int(max_sessions), 10_000))
        self._stores: OrderedDict[str, VectorStoreService] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> VectorStoreService:
        sid = session_id.strip()
        if not is_valid_session_id(sid):
            raise ValueError("Invalid session id")

        with self._lock:
            if sid in self._stores:
                self._stores.move_to_end(sid)
                return self._stores[sid]

            svc = VectorStoreService(session_id=sid)
            # Read-only probes and rejected questions must not evict real documents.
            if svc.is_ready:
                self._remember(svc)
            return svc

    def _remember(self, service: VectorStoreService) -> None:
        while len(self._stores) >= self._max:
            evicted_sid, evicted_svc = self._stores.popitem(last=False)
            evicted_svc.discard_persisted_index_if_idle()
            logger.info("Evicted LRU vector session %s", evicted_sid)
        self._stores[service.session_id] = service

    def activate(self, service: VectorStoreService) -> VectorStoreService:
        """Register only a validated upload, and serialize same-session index writes."""
        with self._lock:
            existing = self._stores.get(service.session_id)
            if existing is not None:
                self._stores.move_to_end(service.session_id)
                return existing
            self._remember(service)
            return service
