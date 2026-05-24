"""Shared pytest fixtures for the backend test suite."""

import pytest


@pytest.fixture(autouse=True)
def _relax_rate_limiter(monkeypatch):
    """Disable rate-limit caps for tests so the suite can hit the endpoint freely.

    The middleware reads these module-level constants on every request, so
    bumping them here neutralises both the per-window and per-day caps.
    """
    monkeypatch.setattr("middleware.rate_limiter.MAX_REQUESTS_PER_WINDOW", 10**9)
    monkeypatch.setattr("middleware.rate_limiter.MAX_REQUESTS_PER_DAY", 10**9)
