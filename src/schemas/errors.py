from pydantic import BaseModel, JsonValue


class ErrorResponse(BaseModel):
    """Описывает стандартный ответ API с сообщением и кодом ошибки."""

    detail: str
    code: str | None = None


class ValidationErrorResponse(BaseModel):
    """Описывает ответ API со списком ошибок проверки запроса."""

    detail: str
    errors: list[dict[str, JsonValue]]
