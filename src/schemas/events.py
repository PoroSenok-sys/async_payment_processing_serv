from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.models.enums import Currency, PaymentStatus


class PaymentEvent(BaseModel):
    """Проверяет идентификаторы входящего события обработки платежа."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    payment_id: int = Field(strict=True, gt=0, le=2147483647)


class PaymentWebhook(BaseModel):
    """Описывает уведомление о сохранённом финальном результате платежа."""

    event_id: UUID
    payment_id: int
    amount: Decimal
    currency: Currency
    status: Literal[PaymentStatus.SUCCEEDED, PaymentStatus.FAILED]
    processed_at: datetime

    @field_serializer("amount", when_used="json")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value, ".2f")
