"""Создаёт таблицы платежей и транзакционных событий outbox.

Идентификатор ревизии: 0001
Предыдущая ревизия:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

currency = postgresql.ENUM("RUB", "USD", "EUR", name="payment_currency", create_type=False)
payment_status = postgresql.ENUM(
    "pending", "succeeded", "failed", name="payment_status", create_type=False
)


def upgrade() -> None:
    currency.create(op.get_bind(), checkfirst=True)
    payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", payment_status, server_default="pending", nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0 AND amount < 'Infinity'::numeric", name="amount_positive_finite"),
        sa.CheckConstraint("amount = trunc(amount, 2)", name="amount_decimal_places"),
        sa.CheckConstraint("jsonb_typeof(meta) = 'object'", name="meta_object"),
        sa.CheckConstraint("idempotency_key <> ''", name="idempotency_key_not_empty"),
        sa.CheckConstraint("webhook_url <> ''", name="webhook_url_not_empty"),
        sa.CheckConstraint(
            "(status = 'pending' AND processed_at IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND processed_at IS NOT NULL)",
            name="status_processed_at",
        ),
        sa.UniqueConstraint("idempotency_key"),
    )

    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        sa.CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        sa.CheckConstraint("event_type <> ''", name="event_type_not_empty"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_outbox_payment_id", "outbox", ["payment_id"])
    op.create_index(
        "ix_outbox_pending", "outbox", ["next_attempt_at", "id"],
        postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("outbox")
    op.drop_table("payments")
    payment_status.drop(op.get_bind(), checkfirst=True)
    currency.drop(op.get_bind(), checkfirst=True)
