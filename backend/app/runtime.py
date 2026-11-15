"""Reversible Lambda entry wrapper. Business handlers remain unchanged."""

import importlib
import json
import os
import re
from urllib.parse import urlsplit

import boto3

_trace = {}
_installed = False


def trace_from(event):
    headers = {k.lower(): str(v) for k, v in event.get("headers", {}).items()}
    run = headers.get("x-pitwall-run", event.get("_pitwall_run", ""))
    phase = headers.get("x-pitwall-phase", event.get("_pitwall_phase", "live"))
    attributes = event.get("messageAttributes", {})
    if not attributes and event.get("body"):
        try:
            attributes = json.loads(event["body"]).get("MessageAttributes", {})
        except (ValueError, AttributeError):
            pass
    for name, destination in [("pitwall_run", "run"), ("pitwall_phase", "phase")]:
        attr = attributes.get(name, {})
        value = attr.get("stringValue", attr.get("Value", ""))
        if value and destination == "run":
            run = value
        if value and destination == "phase":
            phase = value
    if not re.fullmatch(r"[a-f0-9]{32}", str(run)):
        return {"run": "", "phase": "live"}
    return {"run": run, "phase": phase if phase in {"baseline", "during", "recovery"} else "live"}


def headers(request, **kwargs):
    request.headers["X-Pitwall-Caller"] = os.environ["AWS_LAMBDA_FUNCTION_NAME"]
    if _trace.get("run"):
        request.headers["X-Pitwall-Run"] = _trace["run"]
        request.headers["X-Pitwall-Phase"] = _trace["phase"]


def parameters(params, model, **kwargs):
    # Queue URLs otherwise let some SQS SDK versions bypass a custom endpoint.
    if "QueueUrl" in params:
        params["QueueUrl"] = (
            os.environ["PITWALL_GATEWAY_URL"].rstrip("/") + urlsplit(params["QueueUrl"]).path
        )
    if not _trace.get("run"):
        return
    if model.name in {"SendMessage", "Publish"}:
        attributes = params.setdefault("MessageAttributes", {})
        for name in ["run", "phase"]:
            attributes["pitwall_" + name] = {"DataType": "String", "StringValue": _trace[name]}
    if model.name == "StartExecution":
        payload = json.loads(params.get("input", "{}"))
        payload.update(_pitwall_run=_trace["run"], _pitwall_phase=_trace["phase"])
        params["input"] = json.dumps(payload)


def install():
    global _installed
    if _installed:
        return
    gateway = os.environ["PITWALL_GATEWAY_URL"]
    if gateway != "http://pitwall-gateway:8000":
        raise RuntimeError("Only the local Pitwall gateway is supported")
    os.environ["AWS_ENDPOINT_URL"] = gateway
    # Bound SDK retries, without changing the application's own retry/DLQ logic.
    os.environ["AWS_MAX_ATTEMPTS"] = "2"
    os.environ["AWS_RETRY_MODE"] = "standard"
    boto3.setup_default_session()
    boto3.DEFAULT_SESSION.events.register("before-sign", headers)
    boto3.DEFAULT_SESSION.events.register("before-parameter-build", parameters)
    _installed = True


def handle(event, context):
    global _trace
    install()
    handler = importlib.import_module("handler").lambda_handler
    if "Records" in event:
        result = None
        for record in event["Records"]:
            _trace = trace_from(record)
            result = handler({**event, "Records": [record]}, context)
        return result
    _trace = trace_from(event)
    return handler(event, context)
