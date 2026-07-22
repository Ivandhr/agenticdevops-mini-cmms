"""Tests for GET /health."""

from fastapi.testclient import TestClient

from app.main import DEV_RENDERER_ORIGIN, app

client = TestClient(app)

ALLOW_ORIGIN_HEADER = "access-control-allow-origin"


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_allows_the_dev_renderer_origin() -> None:
    """The backend *emits* the header the renderer's browser requires.

    Note what this cannot show: `TestClient` calls the ASGI app in-process,
    where no browser exists, so it never proves Chromium accepts the response
    (TRAP-001). Its job is to stop the middleware being silently removed or
    misconfigured later; the boundary itself is proven by running the app.
    """
    response = client.get("/health", headers={"Origin": DEV_RENDERER_ORIGIN})

    assert response.status_code == 200
    assert response.headers[ALLOW_ORIGIN_HEADER] == DEV_RENDERER_ORIGIN


def test_health_does_not_allow_an_unlisted_origin() -> None:
    """The allowlist is an allowlist — this is the no-wildcard guard."""
    response = client.get("/health", headers={"Origin": "http://example.invalid"})

    assert ALLOW_ORIGIN_HEADER not in response.headers


def test_health_does_not_allow_the_null_origin() -> None:
    """`Origin: null` (the packaged `file://` renderer) stays off the list.

    Deliberate, not an oversight: "null" is not a real origin — sandboxed
    iframes send it too. The packaged app gets a registered custom scheme
    instead; see `checklists/packaging-preflight.checklist.md`.
    """
    response = client.get("/health", headers={"Origin": "null"})

    assert ALLOW_ORIGIN_HEADER not in response.headers
