"""
Base Agent Class

Abstract base class for all agents in the pipeline.
Defines the interface and common functionality.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    success: bool
    data: Any
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    def process(self, input_data: Any, context: dict[str, Any]) -> Any:
        pass

    def execute(self, input_data: Any, context: dict[str, Any]) -> AgentResult:
        start_time = time.time()

        try:
            result = self.process(input_data, context)
            duration_ms = (time.time() - start_time) * 1000

            return AgentResult(
                success=True, data=result, duration_ms=duration_ms, metadata={"agent": self.name}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            return AgentResult(
                success=False,
                data=None,
                error=str(e),
                duration_ms=duration_ms,
                metadata={"agent": self.name},
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
