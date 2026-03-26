"""API middleware — logging, error handling, request tracking."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and correlation ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Attach request ID to state
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            elapsed = round(time.time() - start, 3)
            logger.info(
                "api.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed=elapsed,
                request_id=request_id,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            logger.error(
                "api.error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                elapsed=elapsed,
                request_id=request_id,
            )
            raise


def add_middleware(app: FastAPI) -> None:
    """Register all middleware on the app."""
    app.add_middleware(RequestLoggingMiddleware)
