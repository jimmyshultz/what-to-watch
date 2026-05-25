"""Tests for the per-IP rate limiter middleware."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from main import app
from models.schemas import RecommendResponse


def _stub_response() -> RecommendResponse:
    return RecommendResponse(query="x", recommendations=[])


def _find_rate_limiter():
    """Walk Starlette's built middleware stack to find the live
    RateLimiterMiddleware instance so tests can reset its bucket.

    The stack is built lazily on the first request — trigger that with a
    cheap health check if it hasn't been built yet.
    """
    if app.middleware_stack is None:
        TestClient(app).get("/health")
    node = app.middleware_stack
    while node is not None:
        if type(node).__name__ == "RateLimiterMiddleware":
            return node
        node = getattr(node, "app", None)
    raise RuntimeError("RateLimiterMiddleware not found in stack")


@pytest.fixture
def client(monkeypatch):
    """TestClient with real (low) rate-limit caps and a stubbed RAG pipeline.
    Clears the limiter bucket so prior tests don't pollute the count."""
    monkeypatch.setattr("middleware.rate_limiter.MAX_REQUESTS_PER_WINDOW", 3)
    monkeypatch.setattr("middleware.rate_limiter.MAX_REQUESTS_PER_DAY", 5)
    monkeypatch.setattr(
        "routers.recommend.get_recommendations",
        AsyncMock(return_value=_stub_response()),
    )
    limiter = _find_rate_limiter()
    limiter._requests.clear()
    limiter._request_count = 0
    return TestClient(app)


def _payload(q: str = "a movie") -> dict:
    return {"query": q, "watched": [], "ratings": [], "reviews": []}


def test_returns_429_not_500_when_window_limit_exceeded(client):
    """Regression: middleware-raised HTTPException used to bubble past
    FastAPI's handlers and surface as 500. Must be 429 with JSON detail."""
    for _ in range(3):
        assert client.post("/api/recommend", json=_payload()).status_code == 200
    response = client.post("/api/recommend", json=_payload())
    assert response.status_code == 429
    body = response.json()
    assert "detail" in body
    assert "rate limit" in body["detail"].lower()


def test_options_preflight_not_counted_against_window(client):
    """CORS preflights are browser-initiated and shouldn't burn the quota."""
    for _ in range(20):
        r = client.options(
            "/api/recommend",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code in (200, 204)
    # Real POSTs should still be allowed up to the window cap
    for _ in range(3):
        assert client.post("/api/recommend", json=_payload()).status_code == 200


def test_health_endpoint_is_not_rate_limited(client):
    """Health checks (Cloud Run probes) bypass the limiter entirely."""
    for _ in range(20):
        assert client.get("/health").status_code == 200
