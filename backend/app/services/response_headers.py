"""Keep session state out of shared HTTP caches and attach safe diagnostic IDs."""

from uuid import uuid4


class ResponseHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid4().hex.encode()

        async def with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                names = {name.lower() for name, _ in headers}
                for name, value in (
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-request-id", request_id),
                ):
                    if name not in names:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        return await self.app(scope, receive, with_headers)
