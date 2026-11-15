"""Availability probes for the explicitly configured local test environment.

These checks report HTTP availability only, not discovered dependencies, security,
or resilience. Targets are fixed Docker service names, never user-supplied URLs.
"""

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel

LOCALSTACK_URL = "http://localstack:4566/_localstack/health"


class Probe(BaseModel):
    status: Literal["available", "unavailable", "not_configured"]
    latency_ms: int | None = None
    detail: str


class WorkspaceStatus(BaseModel):
    checked_at: datetime
    localstack: Probe


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def is_localstack_ready(body: bytes) -> bool:
    payload = json.loads(body)
    return isinstance(payload, dict) and payload.get("services", {}).get("dynamodb") in {
        "available",
        "running",
    }


def probe(url: str, validate: Callable[[bytes], bool]) -> Probe:
    started = perf_counter()
    detail = "HTTP endpoint responded"
    status = "unavailable"
    try:
        request = Request(url, headers={"User-Agent": "SunHacks-Local-Availability/0.1"})
        with build_opener(NoRedirect).open(request, timeout=2) as response:
            if response.status == 200 and validate(response.read(65536)):
                status = "available"
            else:
                detail = "Unexpected endpoint response"
    except HTTPError as error:
        detail = "HTTP " + str(error.code)
    except (TimeoutError, URLError, OSError):
        detail = "Endpoint did not respond within the local check"
    except (ValueError, TypeError, AttributeError):
        detail = "Unexpected endpoint response"
    return Probe(
        status=status,
        latency_ms=round((perf_counter() - started) * 1000),
        detail=detail,
    )


def workspace_status() -> WorkspaceStatus:
    localstack = Probe(status="not_configured", detail="Local AWS profile is not enabled")
    if os.environ.get("LOCALSTACK_ENABLED") == "1":
        localstack = probe(LOCALSTACK_URL, is_localstack_ready)
    return WorkspaceStatus(
        checked_at=datetime.now(UTC),
        localstack=localstack,
    )
