from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workspace import LOCALSTACK_URL, is_localstack_ready, probe


def response(body, status=200):
    result = MagicMock()
    result.__enter__.return_value.status = status
    result.__enter__.return_value.read.return_value = body
    return result


def test_unconfigured_workspace_performs_no_network_requests(monkeypatch):
    monkeypatch.delenv("LOCALSTACK_ENABLED", raising=False)
    opener = MagicMock()
    monkeypatch.setattr("app.workspace.build_opener", opener)
    with TestClient(app) as client:
        result = client.get("/api/workspace")
    assert result.status_code == 200
    assert "sample" not in result.json()
    assert result.json()["localstack"]["status"] == "not_configured"
    assert result.json()["checked_at"].endswith("Z")
    opener.assert_not_called()


def test_configured_workspace_checks_only_localstack(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_ENABLED", "1")
    opener = MagicMock()
    opener.open.side_effect = [
        response(b'{"services":{"dynamodb":"available"}}'),
    ]
    monkeypatch.setattr("app.workspace.build_opener", lambda *args: opener)
    with TestClient(app) as client:
        result = client.get("/api/workspace").json()
    assert "sample" not in result
    assert result["localstack"]["status"] == "available"
    assert opener.open.call_count == 1
    assert opener.open.call_args_list[0].args[0].full_url == LOCALSTACK_URL
    assert opener.open.call_args_list[0].kwargs["timeout"] == 2


@pytest.mark.parametrize(
    "body,status,expected",
    [
        (b'{"services":{"dynamodb":"available"}}', 200, "available"),
        (b"{}", 200, "unavailable"),
    ],
)
def test_readiness_check_validates_response(monkeypatch, body, status, expected):
    opener = MagicMock()
    opener.open.return_value = response(body, status)
    monkeypatch.setattr("app.workspace.build_opener", lambda *args: opener)
    result = probe(LOCALSTACK_URL, is_localstack_ready)
    assert result.status == expected
    assert result.latency_ms is not None


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError(),
        URLError("connection refused"),
        HTTPError(LOCALSTACK_URL, 302, "redirect", {}, None),
        HTTPError(LOCALSTACK_URL, 503, "unavailable", {}, None),
    ],
)
def test_endpoint_failures_are_not_reported_as_available(monkeypatch, error):
    opener = MagicMock()
    opener.open.side_effect = error
    monkeypatch.setattr("app.workspace.build_opener", lambda *args: opener)
    assert probe(LOCALSTACK_URL, lambda body: True).status == "unavailable"


@pytest.mark.parametrize(
    "body,expected",
    [
        (b'{"services":{"dynamodb":"running"}}', True),
        (b'{"services":{"dynamodb":"disabled"}}', False),
        (b'{"services":{}}', False),
        (b"[]", False),
    ],
)
def test_localstack_requires_dynamodb_readiness(body, expected):
    assert is_localstack_ready(body) == expected


def test_malformed_localstack_response_is_unavailable(monkeypatch):
    opener = MagicMock()
    opener.open.return_value = response(b"not json")
    monkeypatch.setattr("app.workspace.build_opener", lambda *args: opener)
    assert probe("http://localstack:4566/_localstack/health", is_localstack_ready).status == (
        "unavailable"
    )
