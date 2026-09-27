"""Optional telemetry relay, restricted to the deployment's single configured DSN."""

import hmac
import json
import logging
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, Request, Response

from ..config import get_settings
from ..services.ip_rate_limit import check_ask_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Oversight & Monitoring"])


def _upstream(dsn: str) -> str | None:
    try:
        parsed = urlsplit(dsn)
        host = parsed.hostname or ""
        project = parsed.path.strip("/")
        if (
            parsed.scheme != "https"
            or parsed.port not in (None, 443)
            or not parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not host.endswith(".sentry.io")
            or not project.isdigit()
        ):
            return None
        return f"https://{host}/api/{project}/envelope/"
    except ValueError:
        return None


@router.post("/api/oversight", dependencies=[Depends(check_ask_rate_limit)])
async def sentry_tunnel(request: Request) -> Response:
    configured = get_settings().telemetry_tunnel_dsn
    if not configured:
        return Response(status_code=404)
    upstream = _upstream(configured)
    if upstream is None:
        return Response(status_code=503)
    body = await request.body()
    try:
        header = json.loads(body.split(b"\n", 1)[0])
        dsn = header.get("dsn") if isinstance(header, dict) else None
        if not isinstance(dsn, str):
            return Response(status_code=400)
        if not hmac.compare_digest(dsn.encode(), configured.encode()):
            return Response(status_code=403)
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.post(
                upstream,
                content=body,
                headers={"Content-Type": "application/x-sentry-envelope"},
                timeout=10,
            )
        return Response(status_code=204 if response.is_success else 502)
    except (ValueError, UnicodeError):
        return Response(status_code=400)
    except httpx.HTTPError:
        logger.warning("Telemetry relay failed")
        return Response(status_code=502)
