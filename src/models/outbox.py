from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Outbox(Base):
    """Событие платежа с состоянием публикации, обработки и повторной доставки."""

    __tablename__ = "outbox"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("event_type <> ''", name="event_type_not_empty"),
        CheckConstraint("consumer_attempts BETWEEN 0 AND 3", name="consumer_attempts_range"),
        CheckConstraint(
            "(consumer_state = 'pending' AND consumer_attempts = 0 AND consumer_next_attempt_at IS NULL) OR "
            "(consumer_state IN ('processing', 'completed', 'dead') AND consumer_attempts BETWEEN 1 AND 3 "
            "AND consumer_next_attempt_at IS NULL) OR "
            "(consumer_state = 'retry' AND consumer_attempts BETWEEN 1 AND 2 "
            "AND consumer_next_attempt_at IS NOT NULL)",
            name="consumer_state",
        ),
        Index(
            "ix_outbox_pending",
            "next_attempt_at",
            "id",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[UUID] = mapped_column(Uuid, default=uuid4, unique=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    consumer_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    consumer_state: Mapped[str] = mapped_column(Text, default="pending", server_default="pending", nullable=False)
    consumer_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumer_last_error: Mapped[str | None] = mapped_column(Text)
