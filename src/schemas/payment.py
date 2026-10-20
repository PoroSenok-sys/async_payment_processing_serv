from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_serializer, field_validator

from src.models.enums import Currency, PaymentStatus
from src.schemas.types import WebhookUrl


class PaymentCreate(BaseModel):
    """Проверяет данные запроса создания платежа и задаёт необязательные значения."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    amount: Annotated[
        Decimal,
        Field(
            gt=0,
            decimal_places=2,
            allow_inf_nan=False,
            description="Положительная десятичная строка с точностью до двух знаков после запятой",
            examples=["100.00"],
        ),
    ]
    currency: Currency
    description: str = ""
    meta: dict[str, JsonValue] = Field(default_factory=dict)
    webhook_url: WebhookUrl

    @field_validator("amount", mode="before", json_schema_input_type=str)
    @classmethod
    def require_decimal_string(cls, value: Any) -> str:
        # Дробные JSON-числа могут потерять точность до проверки десятичной суммы.
        if not isinstance(value, str):
            raise ValueError("amount must be a decimal string")
        return value


class PaymentAccepted(BaseModel):
    """Описывает ответ о принятом или ранее созданном платеже."""

    model_config = ConfigDict(from_attributes=True)

    payment_id: int = Field(validation_alias="id")
    status: PaymentStatus
    created_at: datetime


class PaymentDetails(BaseModel):
    """Описывает полный ответ API с данными платежа и датами обработки."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    currency: Currency
    description: str
    meta: dict[str, JsonValue]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None

    @field_serializer("amount", when_used="json")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value, ".2f")
