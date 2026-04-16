import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.metrics import http_request_duration_seconds, http_requests_total

log = structlog.get_logger(__name__)

# Endpoints excluded from per-request logging noise
_SILENT_PATHS = {"/health", "/metrics"}


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        method = request.method
        status = str(response.status_code)

        http_requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

        if endpoint not in _SILENT_PATHS:
            log.info(
                "http.request",
                method=method,
                path=endpoint,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

        response.headers["X-Request-ID"] = request_id
        return response
