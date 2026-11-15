"""Bounded request metadata and experiment reports; request bodies are never stored."""

import json
import sqlite3
import threading
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path=":memory:"):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT)")
            self.db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, run_id TEXT, phase TEXT,
                caller TEXT, service TEXT, operation TEXT, resource TEXT,
                status INTEGER, latency_ms INTEGER, injected INTEGER)""")
        for run in self.runs(100):
            if run["status"] == "running":
                self.update(
                    run["id"],
                    status="interrupted",
                    phase="interrupted",
                    ended_at=now(),
                    message="Pitwall restarted. Faults were cleared; recovery is unverified.",
                )

    def put(self, run):
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?,?)", (run["id"], json.dumps(run))
            )

    def get(self, run_id):
        with self.lock:
            row = self.db.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def update(self, run_id, **fields):
        with self.lock:
            run = self.get(run_id)
            run.update(fields)
            self.put(run)
            return run

    def runs(self, limit=12):
        with self.lock:
            rows = self.db.execute("SELECT data FROM runs ORDER BY rowid DESC LIMIT ?", (limit,))
            return [json.loads(row["data"]) for row in rows]

    def event(self, **values):
        with self.lock, self.db:
            self.db.execute(
                """INSERT INTO events (at,run_id,phase,caller,service,operation,resource,
                   status,latency_ms,injected) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    now(),
                    values.get("run_id", ""),
                    values.get("phase", "live"),
                    values["caller"],
                    values["service"],
                    values["operation"],
                    values["resource"],
                    values["status"],
                    values["latency_ms"],
                    int(values.get("injected", False)),
                ),
            )
            self.db.execute("DELETE FROM events WHERE id < (SELECT MAX(id)-8000 FROM events)")

    def events(self, run_id=None, limit=300):
        with self.lock:
            query = "SELECT * FROM events"
            args = []
            if run_id:
                query += " WHERE run_id=?"
                args.append(run_id)
            query += " ORDER BY id DESC LIMIT ?"
            return [dict(row) for row in self.db.execute(query, (*args, limit))]

    def counts(self, run_id=None):
        with self.lock:
            query = "SELECT service, COUNT(*) AS calls, SUM(status >= 500) AS errors FROM events"
            args = ()
            if run_id:
                query += " WHERE run_id=?"
                args = (run_id,)
            query += " GROUP BY service"
            return {row["service"]: dict(row) for row in self.db.execute(query, args)}
