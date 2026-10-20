from secrets import compare_digest

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class APIKeyMiddleware:
    """Проверка аутентификации каждого HTTP-маршрута."""

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        self.app = app
        self.api_key = api_key.encode("utf-8")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        provided = Headers(scope=scope).get("X-API-Key")
        if provided is None:
            detail, code = "API key is required", "api_key_missing"
        elif not compare_digest(provided.encode("utf-8"), self.api_key):
            detail, code = "Invalid API key", "api_key_invalid"
        else:
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=401,
            content={"detail": detail, "code": code},
            headers={"WWW-Authenticate": "APIKey"},
        )
        await response(scope, receive, send)
