"""Process-wide backpressure for expensive operations (also configure edge limits)."""

import asyncio
from collections.abc import Callable, Generator
from functools import lru_cache
from threading import BoundedSemaphore
from typing import Any

from fastapi import HTTPException

from ..config import get_settings


@lru_cache(maxsize=1)
def _slots() -> BoundedSemaphore:
    return BoundedSemaphore(get_settings().max_concurrent_requests)


@lru_cache(maxsize=1)
def _worker_slots() -> BoundedSemaphore:
    return BoundedSemaphore(get_settings().max_concurrent_requests)


async def run_bounded_worker(function: Callable, *args: Any) -> Any:
    """Cancellation cannot release a CPU slot while its thread is still running."""
    slots = _worker_slots()
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Processing workers are busy. Try again shortly.")

    def run():
        try:
            return function(*args)
        finally:
            slots.release()

    task = asyncio.create_task(asyncio.to_thread(run))
    # A disconnected caller no longer awaits the task. Consume its eventual exception.
    task.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
    await asyncio.wait({task})
    return task.result()


def require_capacity() -> Generator[None, None, None]:
    slots = _slots()
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Server is busy. Try again shortly.", headers={"Retry-After": "5"})
    try:
        yield
    finally:
        slots.release()
