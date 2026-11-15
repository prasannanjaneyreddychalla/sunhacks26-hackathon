"""Baseline/fault/recovery journeys against the connected local Quiz application."""

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import httpx
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.catalog import CAPABILITIES, SERVICES, TARGET_BY_ID, TARGETS
from app.store import now


class Engine:
    def __init__(self, store, faults, data_dir, enabled=False):
        self.store, self.faults, self.enabled = store, faults, enabled
        self.data_dir = Path(data_dir)
        self.lock = threading.RLock()
        self.running = None
        self.stop = threading.Event()
        self.health_cache = (0, False)

    def connection(self):
        path = self.data_dir / "connection.json"
        try:
            connection = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(connection.get("api_id"), str) or not connection["api_id"].isalnum():
            return None
        return connection

    def connected(self):
        connection = self.connection()
        if not self.enabled or not connection:
            return False
        if time.monotonic() - self.health_cache[0] > 8:
            try:
                with httpx.Client(timeout=2, trust_env=False) as client:
                    response = client.get(
                        "http://sunhacks-quiz-lab-localstack-1:4566/_localstack/health"
                    )
                    healthy = response.status_code == 200
                if healthy:
                    config = Config(
                        connect_timeout=2, read_timeout=2, retries={"total_max_attempts": 1}
                    )
                    options = {
                        "endpoint_url": "http://sunhacks-quiz-lab-localstack-1:4566",
                        "region_name": "us-east-1",
                        "aws_access_key_id": "test",
                        "aws_secret_access_key": "test",
                        "config": config,
                    }
                    functions = boto3.client("lambda", **options).list_functions()["Functions"]
                    wired = {
                        item["FunctionName"]
                        for item in functions
                        if item["Handler"] == "pitwall_entry.handle"
                    }
                    healthy = set(connection["functions"]).issubset(wired)
                    apis = boto3.client("apigateway", **options).get_rest_apis()["items"]
                    healthy = healthy and any(item["id"] == connection["api_id"] for item in apis)
            except (httpx.HTTPError, BotoCoreError, ClientError, OSError, KeyError, ValueError):
                healthy = False
            self.health_cache = (time.monotonic(), healthy)
        return self.health_cache[1]

    def status(self, run_id=None):
        runs = self.store.runs()
        selected = self.store.get(run_id) if run_id else (runs[0] if runs else None)
        events = self.store.events(selected["id"] if selected else None)
        counts = self.store.counts(selected["id"] if selected else None)
        all_recent = self.store.events(limit=1000)
        services = []
        for service, label, description in SERVICES:
            measured = counts.get(service, {"calls": 0, "errors": 0})
            latest = next((event for event in all_recent if event["service"] == service), None)
            services.append(
                {
                    "id": service,
                    "label": label,
                    "description": description,
                    "calls": measured["calls"],
                    "errors": measured["errors"],
                    "last_status": latest["status"] if latest else None,
                    "last_seen": latest["at"] if latest else None,
                }
            )
        rule = self.faults.active()
        if rule:
            rule.pop("deadline", None)
        return {
            "brand": "Pitwall",
            "connected": self.connected(),
            "connection": self.connection(),
            "services": services,
            "targets": TARGETS,
            "capabilities": CAPABILITIES,
            "run": selected,
            "runs": [
                {k: run.get(k) for k in ["id", "target_id", "status", "started_at", "phase"]}
                for run in runs
            ],
            "active_run_id": self.running,
            "fault": rule,
            "events": events,
        }

    def start(self, target_id=None, duration=45):
        if target_id is not None and target_id not in TARGET_BY_ID:
            raise ValueError("Choose a supported dependency target")
        if not 20 <= duration <= 60:
            raise ValueError("Choose a fault window between 20 and 60 seconds")
        with self.lock:
            if self.running:
                raise RuntimeError("An experiment is already running")
            if not self.enabled or not self.connection():
                raise ValueError("Connect the local Quiz lab before running a journey")
            run_id = uuid.uuid4().hex
            self.running = run_id
            self.stop.clear()
            self.store.put(
                {
                    "id": run_id,
                    "target_id": target_id,
                    "duration_seconds": duration,
                    "status": "running",
                    "phase": "baseline",
                    "started_at": now(),
                    "phases": {},
                    "actions": [],
                    "message": "Checking the baseline…",
                }
            )
            threading.Thread(target=self.work, args=(run_id,), daemon=True).start()
            return self.store.get(run_id)

    def restore(self):
        self.faults.clear()
        self.stop.set()
        if self.running:
            self.store.update(
                self.running, message="Traffic restored. Finishing the recovery check…"
            )

    def action(self, run_id, label):
        run = self.store.get(run_id)
        self.store.update(run_id, actions=[*run["actions"], {"at": now(), "label": label}])

    def record(self, run_id, phase, capability, status, detail, latency_ms=None):
        with self.store.lock:
            run = self.store.get(run_id)
            phases = run["phases"]
            phases.setdefault(phase, {"started_at": now(), "results": {}})
            phases[phase]["results"][capability] = {
                "status": status,
                "detail": detail,
                "latency_ms": latency_ms,
                "checked_at": now(),
            }
            self.store.update(run_id, phases=phases)

    @staticmethod
    def payload(run_id, phase):
        return {
            "Title": "Pitwall probe " + run_id[:8] + " " + phase,
            "Visibility": "Private",
            "EnableTimer": False,
            "Questions": [
                {
                    "QuestionText": "Which service queues answers?",
                    "Options": ["SQS", "S3", "SES", "IAM"],
                    "CorrectAnswer": "SQS",
                    "Trivia": "A local test fixture.",
                }
            ],
        }

    def phase(self, run_id, phase, quiz_id, existing_id=None):
        self.store.update(
            run_id,
            phase=phase,
            message={
                "baseline": "Checking the baseline…",
                "during": "Measuring the effect of the fault…",
                "recovery": "Traffic restored. Checking recovery…",
            }[phase],
        )
        self.action(
            run_id,
            {
                "baseline": "Baseline started",
                "during": "Fault measurements started",
                "recovery": "Recovery checks started",
            }[phase],
        )
        api_id = self.connection()["api_id"]
        root = "http://pitwall-gateway:8000"
        api = root + "/_aws/execute-api/" + api_id + "/prod"
        headers = {
            "x-pitwall-run": run_id,
            "x-pitwall-phase": phase,
            "x-pitwall-caller": "Journey probe",
        }
        username = "pitwall-" + run_id[:8] + "-" + phase
        with httpx.Client(timeout=8, trust_env=False, headers=headers) as client:

            def request(method, route, **kwargs):
                try:
                    return client.request(method, route, **kwargs)
                except httpx.HTTPError:
                    return None

            def quick(capability, method, route, validate, **kwargs):
                started = time.perf_counter()
                response = request(method, route, **kwargs)
                valid = False
                if response is not None and response.status_code == 200:
                    try:
                        valid = bool(validate(response))
                    except (ValueError, KeyError, TypeError):
                        pass
                detail = (
                    "Expected response verified"
                    if valid
                    else (
                        "Endpoint did not respond within 8 seconds"
                        if response is None
                        else "HTTP "
                        + str(response.status_code)
                        + "; expected result was not returned"
                    )
                )
                self.record(
                    run_id,
                    phase,
                    capability,
                    "pass" if valid else "fail",
                    detail,
                    round((time.perf_counter() - started) * 1000),
                )
                return response

            checks = [
                (
                    "interface",
                    "GET",
                    root + "/quiz-lab-webapp/index.html",
                    lambda r: '<div id="root"' in r.text,
                ),
                (
                    "browse",
                    "GET",
                    api + "/listquizzes",
                    lambda r: isinstance(r.json()["Quizzes"], list),
                ),
                (
                    "open",
                    "GET",
                    api + "/getquiz?quiz_id=" + quiz_id,
                    lambda r: len(r.json()["Questions"]) == 1,
                ),
            ]
            with ThreadPoolExecutor(max_workers=5) as pool:
                jobs = [pool.submit(quick, *check) for check in checks]
                jobs.append(
                    pool.submit(
                        quick,
                        "create",
                        "POST",
                        api + "/createquiz",
                        lambda r: bool(r.json()["QuizID"]),
                        json=self.payload(run_id, phase),
                    )
                )
                if existing_id:
                    jobs.append(
                        pool.submit(
                            quick,
                            "existing",
                            "GET",
                            api + "/getsubmission?submission_id=" + existing_id,
                            lambda r: r.json().get("Score") == 100,
                        )
                    )
                for job in as_completed(jobs):
                    job.result()
            response = quick(
                "submit",
                "POST",
                api + "/submitquiz",
                lambda r: bool(r.json()["SubmissionID"]),
                json={
                    "Username": username,
                    "Email": "user@example.com",
                    "QuizID": quiz_id,
                    "Answers": {"0": {"Answer": "SQS", "TimeTaken": 0}},
                },
            )
            submission_id = None
            if response is not None and response.status_code == 200:
                submission_id = response.json().get("SubmissionID")
            if not submission_id:
                for cap in ["score", "leaderboard", "email"]:
                    self.record(
                        run_id,
                        phase,
                        cap,
                        "blocked",
                        "No submission was accepted; this downstream step was not reached.",
                    )
                if not existing_id:
                    self.record(
                        run_id, phase, "existing", "unknown", "No baseline submission is available."
                    )
                return None
            pending = {"score", "leaderboard", "email"}
            started = time.monotonic()
            deadline = started + 18
            if phase == "during" and self.faults.active():
                deadline = min(deadline, self.faults.active()["deadline"] - 1)
            while pending and time.monotonic() < deadline:
                if phase != "recovery" and self.stop.is_set():
                    break
                if "score" in pending:
                    score = request("GET", api + "/getsubmission?submission_id=" + submission_id)
                    if (
                        score is not None
                        and score.status_code == 200
                        and score.json().get("Score") == 100
                    ):
                        pending.remove("score")
                        self.record(
                            run_id,
                            phase,
                            "score",
                            "pass",
                            "This submission was saved with the expected score: 100.",
                            round((time.monotonic() - started) * 1000),
                        )
                if "leaderboard" in pending:
                    leaders = request("GET", api + "/getleaderboard?quiz_id=" + quiz_id + "&top=50")
                    if (
                        leaders is not None
                        and leaders.status_code == 200
                        and any(
                            row.get("SubmissionID") == submission_id
                            for row in leaders.json()
                            if isinstance(row, dict)
                        )
                    ):
                        pending.remove("leaderboard")
                        self.record(
                            run_id,
                            phase,
                            "leaderboard",
                            "pass",
                            "This phase's new submission appeared on the leaderboard.",
                        )
                if "email" in pending:
                    try:
                        captured = httpx.get(
                            "http://sunhacks-quiz-lab-localstack-1:4566/_aws/ses",
                            timeout=3,
                            trust_env=False,
                        ).json()["messages"]
                        if any(
                            username in (message.get("Body", {}).get("html_part") or "")
                            and "user@example.com"
                            in message.get("Destination", {}).get("ToAddresses", [])
                            for message in captured
                        ):
                            pending.remove("email")
                            self.record(
                                run_id,
                                phase,
                                "email",
                                "pass",
                                "A fresh result email for this submission was captured in LocalStack.",
                            )
                    except (httpx.HTTPError, ValueError, KeyError):
                        pass
                if pending:
                    time.sleep(0.7)
            for cap in pending:
                if phase != "recovery" and self.stop.is_set():
                    self.record(
                        run_id,
                        phase,
                        cap,
                        "unknown",
                        "Stopped before the observation window finished; no conclusion was drawn.",
                    )
                    continue
                status = (
                    "blocked" if cap in {"email", "leaderboard"} and "score" in pending else "fail"
                )
                detail = {
                    "score": "Submission accepted, but its score was not saved within the observation window.",
                    "leaderboard": "The new submission did not appear on the leaderboard.",
                    "email": "No matching result email arrived within the observation window.",
                }[cap]
                if status == "blocked":
                    detail += " The score-saving step did not complete."
                self.record(run_id, phase, cap, status, detail)
            if not existing_id:
                quick(
                    "existing",
                    "GET",
                    api + "/getsubmission?submission_id=" + submission_id,
                    lambda r: r.json().get("Score") == 100,
                )
            phases = self.store.get(run_id)["phases"]
            phases[phase]["ended_at"] = now()
            self.store.update(run_id, phases=phases)
            return submission_id

    def work(self, run_id):
        baseline_id, during_id, quiz_id = None, None, None
        try:
            connection = self.connection()
            api = "http://pitwall-gateway:8000/_aws/execute-api/" + connection["api_id"] + "/prod"
            response = httpx.post(
                api + "/createquiz",
                json=self.payload(run_id, "setup"),
                timeout=12,
                headers={
                    "x-pitwall-run": run_id,
                    "x-pitwall-phase": "baseline",
                    "x-pitwall-caller": "Journey probe",
                },
                trust_env=False,
            )
            response.raise_for_status()
            quiz_id = response.json()["QuizID"]
            self.store.update(run_id, quiz_id=quiz_id)
            baseline_id = self.phase(run_id, "baseline", quiz_id)
            baseline = self.store.get(run_id)["phases"]["baseline"]["results"]
            if any(result["status"] != "pass" for result in baseline.values()) or len(
                baseline
            ) != len(CAPABILITIES):
                self.store.update(
                    run_id,
                    status="stopped" if self.stop.is_set() else "baseline_failed",
                    phase="complete",
                    message="Baseline stopped. No fault was injected."
                    if self.stop.is_set()
                    else "Baseline did not pass. No fault was injected.",
                )
                return
            run = self.store.get(run_id)
            if run["target_id"] and not self.stop.is_set():
                self.faults.arm(run["target_id"], run["duration_seconds"], run_id)
                self.action(run_id, "Fault enabled: " + TARGET_BY_ID[run["target_id"]]["label"])
                try:
                    during_id = self.phase(run_id, "during", quiz_id, baseline_id)
                finally:
                    self.faults.clear()
                    self.action(run_id, "Fault removed; normal traffic restored")
                self.phase(run_id, "recovery", quiz_id, baseline_id)
                if during_id:
                    result = httpx.get(
                        api + "/getsubmission?submission_id=" + during_id,
                        timeout=8,
                        trust_env=False,
                    )
                    self.store.update(
                        run_id,
                        interrupted_submission={
                            "id": during_id,
                            "recovered": result.status_code == 200,
                            "detail": "The submission accepted during the fault "
                            + (
                                "has a saved result."
                                if result.status_code == 200
                                else "still has no saved result after recovery. This is an observed gap, not proof of permanent loss."
                            ),
                        },
                    )
            stopped = self.stop.is_set()
            self.store.update(
                run_id,
                status="stopped" if stopped else "complete",
                phase="complete",
                message="Traffic restored. Review the measured results."
                if stopped
                else "Checks complete. Review what changed and what recovered.",
            )
        # A worker boundary must audit unexpected probe errors as well as restore traffic.
        except Exception as error:  # noqa: BLE001
            self.store.update(
                run_id,
                status="error",
                phase="complete",
                message="Run interrupted: " + str(error)[:220] + ". Faults have been cleared.",
            )
        finally:
            self.faults.clear()
            self.action(run_id, "Run finished; no active fault remains")
            self.store.update(run_id, ended_at=now())
            with self.lock:
                self.running = None
