from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedUpdatedMixin
from src.models.enums import Currency, PaymentStatus


class Payment(Base, CreatedUpdatedMixin):
    """Платёж и конечный результат его обработки."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0 AND amount < 'Infinity'::numeric", name="amount_positive_finite"),
        CheckConstraint("amount = trunc(amount, 2)", name="amount_decimal_places"),
        CheckConstraint("jsonb_typeof(meta) = 'object'", name="meta_object"),
        CheckConstraint("idempotency_key <> ''", name="idempotency_key_not_empty"),
        CheckConstraint("webhook_url <> ''", name="webhook_url_not_empty"),
        CheckConstraint(
            "(status = 'pending' AND processed_at IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND processed_at IS NOT NULL)",
            name="status_processed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(
            Currency,
            name="payment_currency",
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
