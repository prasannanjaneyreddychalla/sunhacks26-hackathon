"""Pitwall's local experiment controller and AWS request gateway."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.experiments import Engine
from app.gateway import Faults, Gateway
from app.store import Store
from app.workspace import WorkspaceStatus, workspace_status


class Health(BaseModel):
    status: str
    service: str


class RunRequest(BaseModel):
    target_id: str | None = None
    duration_seconds: int = Field(default=45, ge=20, le=60, strict=True)


def create_app(store=None, faults=None, data_dir=None, enabled=None):
    enabled = os.environ.get("PITWALL_ENABLED") == "1" if enabled is None else enabled
    data_dir = data_dir or os.environ.get("PITWALL_DATA_DIR", "/tmp/pitwall")
    if enabled:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
    store = store or Store(str(Path(data_dir) / "pitwall.sqlite") if enabled else ":memory:")
    faults = faults or Faults()
    engine = Engine(store, faults, data_dir, enabled)
    gateway = Gateway("http://sunhacks-quiz-lab-localstack-1:4566", store, faults, enabled)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.restore()
        await gateway.client.aclose()

    app = FastAPI(title="Pitwall", version="0.2.0", lifespan=lifespan)
    app.state.engine, app.state.gateway = engine, gateway
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4567", "http://localhost:8000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=Health)
    def health():
        return Health(status="ok", service="platform-api")

    @app.get("/api/workspace", response_model=WorkspaceStatus)
    def workspace():
        return workspace_status()

    @app.get("/api/pitwall")
    def status(run_id: str | None = None):
        if run_id and not store.get(run_id):
            raise HTTPException(404, "Experiment not found")
        return engine.status(run_id)

    @app.post("/api/experiments", status_code=202)
    def start_run(body: RunRequest):
        try:
            return engine.start(body.target_id, body.duration_seconds)
        except RuntimeError as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/experiments/restore")
    def restore():
        engine.restore()
        return {"restored": True, "active_fault": None}

    @app.api_route(
        "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    )
    async def proxy(request: Request, path: str):
        return await gateway.forward(request)

    return app


app = create_app()
