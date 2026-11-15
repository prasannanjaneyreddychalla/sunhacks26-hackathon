import json
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.catalog import CAPABILITIES
from app.experiments import Engine
from app.gateway import Faults, classify
from app.main import create_app
from app.store import Store, now


def test_fault_expiry_is_enforced_without_a_controller_request():
    clock = [100]
    faults = Faults(lambda: clock[0])
    faults.arm("score-writes", 4, "run")
    assert faults.match("dynamodb", "PutItem", "UserSubmissions")
    assert not faults.match("dynamodb", "GetItem", "UserSubmissions")
    assert not faults.match("dynamodb", "PutItem", "Quizzes")
    clock[0] += 5
    assert not faults.match("dynamodb", "PutItem", "UserSubmissions")


def test_faults_are_scoped_and_only_one_can_be_active():
    faults = Faults()
    faults.arm("submission-queue", 30, "run")
    assert faults.match("sqs", "SendMessage", "http://local/000000000000/QuizSubmissionQueue")
    assert not faults.match("sqs", "SendMessage", "http://local/000000000000/OtherQueue")
    with pytest.raises(ValueError):
        faults.arm("result-email", 30, "other")
    faults.clear()
    assert faults.active() is None


@pytest.mark.parametrize(
    "target,duration", [("unknown", 30), ("score-writes", 0), ("database", 61)]
)
def test_invalid_faults_cannot_be_armed(target, duration):
    with pytest.raises(ValueError):
        Faults().arm(target, duration, "run")


def test_proxy_preserves_application_calls_but_records_no_secrets(tmp_path):
    app = create_app(data_dir=str(tmp_path), enabled=True)
    seen = []

    def upstream(request):
        seen.append(request)
        return httpx.Response(200, json={"Item": {"Score": {"N": "100"}}})

    app.state.gateway.client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post(
            "/",
            json={"TableName": "UserSubmissions", "Secret": "PRIVATE"},
            headers={"X-Amz-Target": "DynamoDB_20120810.GetItem", "Host": "attacker.example"},
        )
        assert response.status_code == 200
        assert seen[0].url.host == "sunhacks-quiz-lab-localstack-1"
        events = app.state.engine.store.events()
        assert events[0]["operation"] == "GetItem"
        assert "PRIVATE" not in json.dumps(events)
        assert "authorization" not in json.dumps(events)


def test_fault_does_not_block_control_api_or_unrelated_calls(tmp_path):
    app = create_app(data_dir=str(tmp_path), enabled=True)
    app.state.gateway.client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    )
    with TestClient(app) as client:
        app.state.engine.faults.arm("score-writes", 30, "run")
        failed = client.post(
            "/",
            json={"TableName": "UserSubmissions"},
            headers={"X-Amz-Target": "DynamoDB_20120810.PutItem"},
        )
        assert failed.status_code == 503
        assert client.get("/api/health").status_code == 200
        assert (
            client.post(
                "/",
                json={"TableName": "Quizzes"},
                headers={"X-Amz-Target": "DynamoDB_20120810.GetItem"},
            ).status_code
            == 200
        )
        assert client.post("/api/experiments/restore").json()["restored"] is True
        assert client.post("/api/experiments/restore").json()["restored"] is True
        assert (
            client.post(
                "/",
                json={"TableName": "UserSubmissions"},
                headers={"X-Amz-Target": "DynamoDB_20120810.PutItem"},
            ).status_code
            == 200
        )


def test_unknown_api_routes_never_reach_upstream(tmp_path):
    app = create_app(data_dir=str(tmp_path), enabled=True)
    app.state.gateway.client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: pytest.fail("Control request leaked upstream")
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/unknown").status_code == 404
        assert (
            client.post(
                "/api/experiments", json={"target_id": "anything", "duration_seconds": 600}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/experiments", json={"target_id": "anything", "duration_seconds": 30}
            ).status_code
            == 400
        )


def test_worker_failure_always_restores_traffic(tmp_path, monkeypatch):
    (tmp_path / "connection.json").write_text('{"api_id":"testapi"}')
    store, faults = Store(), Faults()
    engine = Engine(store, faults, str(tmp_path), True)
    run_id = "a" * 32
    engine.running = run_id
    store.put(
        {
            "id": run_id,
            "status": "running",
            "phase": "baseline",
            "target_id": "score-writes",
            "duration_seconds": 30,
            "phases": {},
            "actions": [],
            "started_at": now(),
        }
    )
    monkeypatch.setattr(
        "app.experiments.httpx.post",
        lambda *args, **kwargs: httpx.Response(
            200, json={"QuizID": "fixture"}, request=httpx.Request("POST", "http://local")
        ),
    )

    def phase(run_id, name, *args):
        if name == "during":
            assert faults.active()
            raise RuntimeError("probe crashed")
        store.update(
            run_id,
            phases={
                "baseline": {"results": {cap["id"]: {"status": "pass"} for cap in CAPABILITIES}}
            },
        )
        return "baseline-submission"

    monkeypatch.setattr(engine, "phase", phase)
    engine.work(run_id)
    assert faults.active() is None
    assert engine.running is None
    assert store.get(run_id)["status"] == "error"
    assert "probe crashed" in store.get(run_id)["message"]


def test_restart_marks_unfinished_runs_as_interrupted(tmp_path):
    path = str(tmp_path / "state.sqlite")
    first = Store(path)
    first.put({"id": "run", "status": "running", "phase": "during", "actions": []})
    second = Store(path)
    assert second.get("run")["status"] == "interrupted"
    assert "recovery is unverified" in second.get("run")["message"]
    assert Faults().active() is None


def test_aws_query_requests_are_identified():
    service, operation, resource = classify(
        "POST",
        "/",
        {"authorization": "AWS4-HMAC-SHA256 Credential=test/20261115/us-east-1/sns/aws4_request"},
        b"Action=Publish&TopicArn=arn%3Aaws%3Asns%3Aus-east-1%3A000000000000%3AQuizzesWriteFailures",
    )
    assert (service, operation, resource) == (
        "sns",
        "Publish",
        "arn:aws:sns:us-east-1:000000000000:QuizzesWriteFailures",
    )


def test_service_counts_include_events_beyond_the_visible_page():
    store = Store()
    for _ in range(305):
        store.event(
            run_id="run",
            phase="during",
            caller="ScoringFunction",
            service="dynamodb",
            operation="PutItem",
            resource="UserSubmissions",
            status=503,
            latency_ms=0,
            injected=True,
        )
    assert len(store.events("run")) == 300
    assert store.counts("run")["dynamodb"]["calls"] == 305
    assert store.counts("run")["dynamodb"]["errors"] == 305


def test_redeployed_unwrapped_functions_are_not_reported_connected(tmp_path, monkeypatch):
    (tmp_path / "connection.json").write_text(
        '{"api_id":"testapi","functions":["ScoringFunction"]}'
    )
    http = MagicMock()
    http.__enter__.return_value.get.return_value.status_code = 200
    monkeypatch.setattr("app.experiments.httpx.Client", lambda **kwargs: http)
    aws = MagicMock()
    aws.list_functions.return_value = {
        "Functions": [{"FunctionName": "ScoringFunction", "Handler": "handler.lambda_handler"}]
    }
    aws.get_rest_apis.return_value = {"items": [{"id": "testapi"}]}
    monkeypatch.setattr("app.experiments.boto3.client", lambda *args, **kwargs: aws)
    engine = Engine(Store(), Faults(), str(tmp_path), True)
    assert not engine.connected()


def test_trace_metadata_survives_sqs_and_sns_envelopes(monkeypatch):
    from app import runtime

    monkeypatch.setenv("PITWALL_GATEWAY_URL", "http://pitwall-gateway:8000")
    monkeypatch.setattr(runtime, "_trace", {"run": "a" * 32, "phase": "during"})
    params = {"QueueUrl": "http://sqs.localhost:4566/000000000000/QuizSubmissionQueue"}
    model = MagicMock()
    model.name = "SendMessage"
    runtime.parameters(params, model)
    assert params["QueueUrl"].startswith("http://pitwall-gateway:8000/")
    assert params["MessageAttributes"]["pitwall_run"]["StringValue"] == "a" * 32
    record = {
        "messageAttributes": {
            key: {"stringValue": value["StringValue"]}
            for key, value in params["MessageAttributes"].items()
        }
    }
    assert runtime.trace_from(record) == runtime._trace
    sns = {
        "body": json.dumps(
            {
                "MessageAttributes": {
                    key: {"Value": value["StringValue"]}
                    for key, value in params["MessageAttributes"].items()
                }
            }
        )
    }
    assert runtime.trace_from(sns) == runtime._trace


def test_cancelled_observation_is_unknown_instead_of_a_false_failure(tmp_path, monkeypatch):
    (tmp_path / "connection.json").write_text('{"api_id":"testapi"}')
    store = Store()
    engine = Engine(store, Faults(), str(tmp_path), True)
    run_id = "a" * 32
    store.put({"id": run_id, "status": "running", "phase": "during", "phases": {}, "actions": []})
    original_client = httpx.Client

    def upstream(request):
        path = request.url.path
        if path.endswith("index.html"):
            return httpx.Response(200, text='<div id="root"></div>')
        body = {
            "listquizzes": {"Quizzes": []},
            "getquiz": {"Questions": [{}]},
            "createquiz": {"QuizID": "new"},
            "submitquiz": {"SubmissionID": "new"},
            "getsubmission": {"Score": 100},
        }.get(path.rsplit("/", 1)[-1], {})
        return httpx.Response(200, json=body)

    monkeypatch.setattr(
        "app.experiments.httpx.Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs),
    )
    engine.stop.set()
    engine.phase(run_id, "during", "fixture", "existing")
    results = store.get(run_id)["phases"]["during"]["results"]
    assert all(results[key]["status"] == "unknown" for key in ["score", "leaderboard", "email"])
