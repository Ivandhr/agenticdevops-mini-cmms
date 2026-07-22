"""CMMess backend — FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

#: The dev renderer's page origin. Vite serves the renderer here and Electron
#: loads that URL, so this is the `Origin` the browser puts on every request to
#: the backend at :8000. Without it on the allowlist Chromium blocks the
#: response and the renderer reports a dead backend while the backend is fine
#: (BUG-001 / TRAP-001).
DEV_RENDERER_ORIGIN = "http://127.0.0.1:5173"


class HealthResponse(BaseModel):
    """Response model for GET /health."""

    status: Literal["ok"]


app = FastAPI(title="CMMess Backend")

# Exactly one origin, no wildcard. `allow_origins=["*"]` is forbidden here: auth
# lands next (DEC-005), and a wildcard combined with credentials is a real
# vulnerability — the allowlist is tight now, while it costs nothing.
#
# The literal "null" origin is deliberately absent. The packaged app loads over
# `file://` and sends `Origin: null`, but "null" is not a real origin — sandboxed
# iframes send it too — so allowlisting it would be permanently loose. The
# packaged case is a recorded blocker in
# `checklists/packaging-preflight.checklist.md`, to be solved with a registered
# custom scheme rather than a loose entry here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[DEV_RENDERER_ORIGIN],
    # What the renderer actually does today. Widen deliberately, per method and
    # per header, when an endpoint needs it.
    allow_methods=["GET"],
    allow_headers=[],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check. No auth."""
    return HealthResponse(status="ok")
