"""Добавляет состояние попыток обработки отдельно от попыток публикации outbox.

Идентификатор ревизии: 0002
Предыдущая ревизия: 0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("outbox", sa.Column("consumer_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("outbox", sa.Column("consumer_state", sa.Text(), server_default="pending", nullable=False))
    op.add_column("outbox", sa.Column("consumer_next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("outbox", sa.Column("consumer_last_error", sa.Text()))
    op.create_check_constraint("consumer_attempts_range", "outbox", "consumer_attempts BETWEEN 0 AND 3")
    op.create_check_constraint(
        "consumer_state", "outbox",
        "(consumer_state = 'pending' AND consumer_attempts = 0 AND consumer_next_attempt_at IS NULL) OR "
        "(consumer_state IN ('processing', 'completed', 'dead') AND consumer_attempts BETWEEN 1 AND 3 "
        "AND consumer_next_attempt_at IS NULL) OR "
        "(consumer_state = 'retry' AND consumer_attempts BETWEEN 1 AND 2 "
        "AND consumer_next_attempt_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_outbox_consumer_state"), "outbox", type_="check")
    op.drop_constraint(op.f("ck_outbox_consumer_attempts_range"), "outbox", type_="check")
    for column in ("consumer_last_error", "consumer_next_attempt_at", "consumer_state", "consumer_attempts"):
        op.drop_column("outbox", column)
