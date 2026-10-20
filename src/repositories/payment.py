from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payment import Payment
from src.repositories.base import SQLAlchemyRepository


class PaymentRepository(SQLAlchemyRepository[Payment]):
    """Выполняет запросы платежей, включая идемпотентную вставку и блокировку строки."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Payment, db)

    async def get_for_update(self, payment_id: int) -> Payment | None:
        statement = select(Payment).where(Payment.id == payment_id).with_for_update()
        return await self.db.scalar(statement)

    async def create_if_absent(self, values: dict[str, Any]) -> Payment | None:
        statement = (
            insert(Payment)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[Payment.idempotency_key])
            .returning(Payment)
        )
        return await self.db.scalar(statement)

    async def get_matching_request(self, values: dict[str, Any]) -> Payment | None:
        statement = select(Payment).where(
            *(getattr(Payment, field) == value for field, value in values.items())
        )
        return await self.db.scalar(statement)
