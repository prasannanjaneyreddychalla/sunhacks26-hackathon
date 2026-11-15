"""Exercise all supported local fault targets. Run inside the Pitwall backend container."""

import json
import time
from pathlib import Path

import httpx

ROOT = "http://127.0.0.1:8000"
CASES = {
    "score-writes": {"score", "leaderboard", "email"},
    "submission-queue": {"submit", "score", "leaderboard", "email"},
    "result-email": {"email"},
    "email-workflow": {"email"},
    "database": {"browse", "open", "create", "submit", "score", "leaderboard", "email", "existing"},
    "quiz-api": {"browse", "open", "create", "submit", "score", "leaderboard", "email", "existing"},
    "frontend": {"interface"},
}


def wait(client, run_id):
    deadline = time.monotonic() + 120
    previous = None
    while time.monotonic() < deadline:
        snapshot = client.get(ROOT + "/api/pitwall", params={"run_id": run_id}).raise_for_status().json()
        run = snapshot["run"]
        state = (run["status"], run["phase"])
        if state != previous:
            print(run["target_id"], run_id[:8], *state, flush=True)
            previous = state
        if run["status"] != "running":
            return snapshot
        time.sleep(1)
    raise AssertionError("Experiment did not finish within 120 seconds")


def main():
    report = []
    with httpx.Client(timeout=12, trust_env=False) as client:
        try:
            for target, expected in CASES.items():
                latest = client.get(ROOT + "/api/pitwall").raise_for_status().json()["run"]
                if target == "score-writes" and latest and latest["target_id"] == target:
                    run_id = latest["id"]
                else:
                    run_id = client.post(ROOT + "/api/experiments", json={"target_id": target, "duration_seconds": 45}).raise_for_status().json()["id"]
                snapshot = wait(client, run_id)
                run = snapshot["run"]
                assert run["status"] == "complete", run
                for phase in ["baseline", "recovery"]:
                    results = run["phases"][phase]["results"]
                    assert len(results) == 9 and all(value["status"] == "pass" for value in results.values()), (target, phase, results)
                results = run["phases"]["during"]["results"]
                affected = {key for key, value in results.items() if value["status"] in {"fail", "blocked"}}
                assert affected == expected, (target, affected, expected, results)
                injected = [event for event in snapshot["events"] if event["injected"]]
                assert injected, "No injected request was observed for " + target
                assert snapshot["fault"] is None
                item = {"target": target, "run_id": run_id, "baseline": 9, "recovery": 9,
                        "during": {key: value["status"] for key, value in results.items()},
                        "injected_requests": len(injected), "interrupted_submission": run.get("interrupted_submission")}
                report.append(item)
                Path("/data/verification.json").write_text(json.dumps(report, indent=2))
                print("VERIFIED", target, "affected:", sorted(affected), "recovery: 9/9", flush=True)
        finally:
            client.post(ROOT + "/api/experiments/restore").raise_for_status()
    print("ALL SEVEN LOCAL TARGETS VERIFIED", flush=True)


if __name__ == "__main__":
    main()
