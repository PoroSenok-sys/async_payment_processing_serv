from typing import Any


class AppError(Exception):
    """Ошибка приложения с единым форматом ответа API."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 500,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details
