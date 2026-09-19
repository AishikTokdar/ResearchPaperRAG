"""Reject oversized requests before parsing or indexing them."""

from fastapi import HTTPException
from starlette.responses import JSONResponse

from ..config import get_settings
from .request_limits import require_capacity


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = (
            get_settings().max_file_size + 1048576
            if scope["path"] in {"/upload", "/api/analyze/stream"}
            else 131072
        )
        headers = dict(scope.get("headers", []))
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = limit + 1
        if content_length < 0 or content_length > limit:
            return await JSONResponse(
                {"detail": "Request body exceeds the size limit"}, status_code=413
            )(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > limit:
                raise HTTPException(413, "Request body exceeds the size limit")
            return message

        expensive = scope["path"] in {
            "/api/oversight",
            "/upload",
            "/ask",
            "/ask/stream",
            "/status",
            "/api/papers/search",
            "/api/papers/ingest",
            "/api/analyze/gaps",
            "/api/analyze/stream",
            "/api/chat/followup",
        }
        capacity = require_capacity() if expensive else None
        if capacity is not None:
            try:
                next(capacity)
            except HTTPException as exc:
                return await JSONResponse(
                    {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
                )(scope, receive, send)
        try:
            return await self.app(scope, limited_receive, send)
        finally:
            if capacity is not None:
                capacity.close()
