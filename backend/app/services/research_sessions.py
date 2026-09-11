"""Bounded anonymous sessions; published engines remain immutable during reads."""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings
from .gap_analyzer_engine import GapAnalyzerEngine


@dataclass
class ResearchSession:
    session_id: str = ""
    papers: dict[str, dict[str, Any]] = field(default_factory=dict)
    engine: GapAnalyzerEngine | None = None
    lock: Any = field(default_factory=threading.Lock)
    prepared_key: str = ""
    prepared_at: float = 0.0
    touched: float = field(default_factory=time.monotonic)


class ResearchSessionRegistry:
    def __init__(self):
        self.sessions: OrderedDict[str, ResearchSession] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, session_id: str, remember: bool = True) -> ResearchSession:
        with self.lock:
            now = time.monotonic()
            for key in [key for key, value in self.sessions.items() if now - value.touched > 86400]:
                del self.sessions[key]
            session = self.sessions.get(session_id)
            if session is None:
                session = ResearchSession(session_id=session_id)
                if remember:
                    self._remember(session)
            session.touched = now
            if session_id in self.sessions:
                self.sessions.move_to_end(session_id)
            return session

    def _remember(self, session: ResearchSession) -> None:
        if session.session_id not in self.sessions:
            while len(self.sessions) >= get_settings().max_vector_sessions:
                self.sessions.popitem(last=False)
        self.sessions[session.session_id] = session
        self.sessions.move_to_end(session.session_id)

    def activate(self, session: ResearchSession) -> None:
        """Only validated source submissions/searches may evict another session."""
        with self.lock:
            self._remember(session)
