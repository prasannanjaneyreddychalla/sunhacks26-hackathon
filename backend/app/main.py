"""Platform foundation. Dependency collection is introduced in later phases."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Application Security & Resilience", version="0.1.0")


class Health(BaseModel):
    status: str
    service: str


@app.get("/api/health", response_model=Health)
def health() -> Health:
    """Process health only; this does not assert application or dependency health."""
    return Health(status="ok", service="platform-api")
