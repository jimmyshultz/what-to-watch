"""Per-IP rate limiting middleware for the FastAPI backend.

Uses an in-memory dictionary to track request timestamps per IP.
Suitable for single-instance Cloud Run deployment.
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


# Rate limit configuration
MAX_REQUESTS_PER_WINDOW = 10  # max requests per window
WINDOW_SECONDS = 600  # 10-minute window
MAX_REQUESTS_PER_DAY = 50
DAY_SECONDS = 86400

# Cleanup interval: remove stale entries every N requests
CLEANUP_INTERVAL = 100


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces per-IP rate limits."""

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._request_count = 0

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For for Cloud Run."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_stale(self, now: float) -> None:
        """Remove entries older than 24 hours."""
        stale_keys = [
            ip for ip, times in self._requests.items()
            if not times or (now - times[-1]) > DAY_SECONDS
        ]
        for key in stale_keys:
            del self._requests[key]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only rate-limit the recommend endpoint
        if not request.url.path.startswith("/api/recommend"):
            return await call_next(request)

        now = time.time()
        client_ip = self._get_client_ip(request)

        # Periodic cleanup
        self._request_count += 1
        if self._request_count % CLEANUP_INTERVAL == 0:
            self._cleanup_stale(now)

        # Get all request timestamps for this IP
        timestamps = self._requests[client_ip]

        # Check window limit (10 requests per 10 minutes)
        recent_window = [t for t in timestamps if now - t < WINDOW_SECONDS]
        if len(recent_window) >= MAX_REQUESTS_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {MAX_REQUESTS_PER_WINDOW} requests per {WINDOW_SECONDS // 60} minutes.",
            )

        # Check daily limit (50 requests per day)
        recent_day = [t for t in timestamps if now - t < DAY_SECONDS]
        if len(recent_day) >= MAX_REQUESTS_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail=f"Daily rate limit exceeded: max {MAX_REQUESTS_PER_DAY} requests per day.",
            )

        # Record this request
        self._requests[client_ip] = recent_day + [now]

        return await call_next(request)
