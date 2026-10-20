import time
import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import with_request_context

logger = logging.getLogger(__name__)


EXCLUDE_PATHS = frozenset(("/healthcheck", "/docs", "/openapi.json"))


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Передаёт или создаёт X-Request-ID и записывает начало и завершение запроса в журнал."""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()

        with with_request_context(request_id=request_id):
            response: Response | None = None
            try:
                response = await call_next(request)
            finally:
                # Не записываем запросы к исключённым путям в журнал.
                if request.url.path not in EXCLUDE_PATHS:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    logger.info(
                        "HTTP %s %s -> %s, %s ms",
                        request.method,
                        request.url.path,
                        (response.status_code if response else "-"),
                        duration_ms,
                    )

            if response is not None:
                response.headers["X-Request-ID"] = request_id
            return response
