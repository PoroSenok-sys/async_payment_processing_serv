from contextlib import asynccontextmanager

from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader

from src.core.config import settings
from src.core.lifespan import lifespan
from src.exceptions.handlers import register_exception_handlers
from src.middlewares.api_key import APIKeyMiddleware
from src.middlewares.request_id import RequestIDMiddleware
from src.routers.payments import router as payments_router
from src.schemas.errors import ErrorResponse, ValidationErrorResponse


@asynccontextmanager
async def api_lifespan(app: FastAPI):
    async with lifespan():
        yield


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=api_lifespan,
    dependencies=[Security(APIKeyHeader(name="X-API-Key", scheme_name="APIKey", auto_error=False))],
    responses={401: {"model": ErrorResponse}, 422: {"model": ValidationErrorResponse}},
)
register_exception_handlers(app)
app.add_middleware(APIKeyMiddleware, api_key=settings.API_KEY.get_secret_value())
app.add_middleware(RequestIDMiddleware)
app.include_router(payments_router)


@app.get("/healthcheck", tags=["health"], summary="Проверить жизнеспособность сервиса")
async def healthcheck() -> dict[str, str]:
    """Проверяет жизнеспособность сервиса."""
    return {"status": "ok"}
