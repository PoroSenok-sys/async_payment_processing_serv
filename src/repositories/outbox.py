from hashlib import blake2b
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.outbox import Outbox
from src.repositories.base import SQLAlchemyRepository


class OutboxRepository(SQLAlchemyRepository[Outbox]):
    """Читает события outbox и управляет блокировками публикации и обработки."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Outbox, db)

    async def get_payment_event(
        self, event_id: UUID, payment_id: int, *, lock: bool = False
    ) -> Outbox | None:
        statement = select(Outbox).where(
            Outbox.event_id == event_id,
            Outbox.payment_id == payment_id,
            Outbox.event_type == "payments.new",
        )
        if lock:
            statement = statement.with_for_update()
        return await self.db.scalar(statement)

    async def try_lock_consumer(self, event_id: UUID) -> bool:
        # Отдельная рекомендательная блокировка позволяет сохранять попытки и результат,
        # не позволяя параллельному дублю начать ещё одну попытку.
        # UUID не повторяет числовые ID строк в разных схемах; хеш одинаков во всех процессах.
        digest = blake2b(event_id.bytes, digest_size=8, person=b"payment-event").digest()
        key = int.from_bytes(digest, byteorder="big", signed=True)
        return bool(await self.db.scalar(select(func.pg_try_advisory_xact_lock(key))))

    async def get_next_ready(self) -> Outbox | None:
        """Блокирует одно готовое событие до фиксации или отката транзакции вызывающим кодом."""
        statement = (
            select(Outbox)
            .where(Outbox.published_at.is_(None), Outbox.next_attempt_at <= func.now())
            .order_by(Outbox.next_attempt_at, Outbox.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return await self.db.scalar(statement)
