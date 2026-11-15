"""Fixed-upstream AWS gateway with scoped, expiring error injection."""

import json
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response

from app.catalog import FUNCTIONS, TARGET_BY_ID

HOP_HEADERS = {
    "host",
    "connection",
    "content-length",
    "transfer-encoding",
    "content-encoding",
    "accept-encoding",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "upgrade",
}


class Faults:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.rule = None

    def active(self):
        with self.lock:
            if self.rule and self.clock() >= self.rule["deadline"]:
                self.rule = None
            return dict(self.rule) if self.rule else None

    def arm(self, target_id, seconds, run_id):
        if target_id not in TARGET_BY_ID or not 1 <= seconds <= 60:
            raise ValueError("Unsupported fault target or duration")
        with self.lock:
            if self.active():
                raise ValueError("Another fault is already active")
            self.rule = {
                "target_id": target_id,
                "run_id": run_id,
                "deadline": self.clock() + seconds,
                "expires_at": (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(),
            }

    def clear(self):
        with self.lock:
            previous = self.rule
            self.rule = None
            return previous

    def match(self, service, operation, resource):
        rule = self.active()
        if not rule:
            return None
        target = TARGET_BY_ID[rule["target_id"]]
        if target["service"] != service:
            return None
        if target["operation"] not in {"*", operation}:
            return None
        if (
            target["resource"]
            and resource.rsplit("/", 1)[-1].rsplit(":", 1)[-1] != target["resource"]
        ):
            return None
        return rule


def classify(method, path, headers, body, query=""):
    service, operation, resource = "unknown", method, ""
    signed = re.search(
        r"Credential=[^/]+/[^/]+/[^/]+/([^/]+)/aws4_request", headers.get("authorization", "")
    )
    if signed:
        service = signed[1]
    service = {"states": "stepfunctions", "execute-api": "apigateway", "email": "ses"}.get(
        service, service
    )
    target = headers.get("x-amz-target", "")
    if target:
        operation = target.rsplit(".", 1)[-1]
        if target.startswith("DynamoDB"):
            service = "dynamodb"
    try:
        data = json.loads(body) if body else {}
    except (ValueError, UnicodeDecodeError):
        data = {key: values[0] for key, values in parse_qs(body.decode(errors="replace")).items()}
    if not isinstance(data, dict):
        data = {}
    if data.get("Action"):
        operation = data["Action"]
    resource = str(
        data.get("TableName")
        or data.get("QueueUrl")
        or data.get("QueueName")
        or data.get("TopicArn")
        or data.get("stateMachineArn")
        or ""
    )
    if path.startswith("/_aws/execute-api/"):
        service, operation, resource = (
            "apigateway",
            method + " " + path.rsplit("/", 1)[-1],
            "QuizAPI",
        )
    elif path.startswith("/quiz-lab-webapp/"):
        service, operation, resource = "s3", "GetObject", "quiz-lab-webapp"
    elif path.startswith("/000000000000/"):
        service, resource = "sqs", path.rsplit("/", 1)[-1]
        operation = data.get("Action", parse_qs(query).get("Action", [operation])[0])
    if "SendEmail" == operation:
        service = "ses"
    return service, operation, resource


def fault_response(service):
    message = "Pitwall: temporary failure injected in the local Quiz lab"
    if service in {"ses", "sns", "s3"}:
        payload = (
            "<ErrorResponse><Error><Type>Receiver</Type><Code>ServiceUnavailable</Code>"
            "<Message>"
            + message
            + "</Message></Error><RequestId>pitwall-local</RequestId></ErrorResponse>"
        )
        return Response(payload, status_code=503, media_type="text/xml")
    error_type = "InternalServerError" if service == "dynamodb" else "ServiceUnavailableException"
    return Response(
        json.dumps({"__type": error_type, "message": message}),
        status_code=503,
        media_type="application/x-amz-json-1.0",
        headers={"x-amzn-errortype": error_type, "x-pitwall-injected": "true"},
    )


class Gateway:
    def __init__(self, upstream, store, faults, enabled=False):
        if upstream != "http://sunhacks-quiz-lab-localstack-1:4566":
            raise ValueError("Only the fixed local Quiz emulator can be targeted")
        self.upstream, self.store, self.faults, self.enabled = upstream, store, faults, enabled
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(20, connect=3), follow_redirects=False, trust_env=False
        )

    async def forward(self, request: Request):
        if not self.enabled or request.url.path.startswith("/api/"):
            raise HTTPException(404, "Route not found")
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0")) > 5_000_000
        ):
            raise HTTPException(413, "Request is too large for the local lab gateway")
        body = await request.body()
        if len(body) > 5_000_000:
            raise HTTPException(413, "Request is too large for the local lab gateway")
        started = time.perf_counter()
        service, operation, resource = classify(
            request.method, request.url.path, request.headers, body, request.url.query
        )
        caller = request.headers.get("x-pitwall-caller", "Browser")
        if caller not in [*FUNCTIONS, "Journey probe"]:
            caller = "Browser"
        run_id = request.headers.get("x-pitwall-run", "")
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            run_id = ""
        phase = request.headers.get("x-pitwall-phase", "live")
        if phase not in {"baseline", "during", "recovery"}:
            phase = "live"
        rule = self.faults.match(service, operation, resource)
        if rule:
            result = fault_response(service)
        else:
            try:
                url = self.upstream + request.url.path
                if request.url.query:
                    url += "?" + request.url.query
                headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
                headers["accept-encoding"] = "identity"
                upstream = await self.client.request(
                    request.method, url, content=body, headers=headers
                )
                result = Response(
                    upstream.content,
                    status_code=upstream.status_code,
                    headers={
                        k: v for k, v in upstream.headers.items() if k.lower() not in HOP_HEADERS
                    },
                )
            except httpx.HTTPError:
                result = Response(
                    '{"message":"Local Quiz emulator did not respond"}',
                    status_code=502,
                    media_type="application/json",
                )
        if service != "unknown":
            self.store.event(
                run_id=run_id,
                phase=phase,
                caller=caller,
                service=service,
                operation=operation[:100],
                resource=resource[:160],
                status=result.status_code,
                injected=bool(rule),
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
        return result
