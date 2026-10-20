from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions.base import AppError
from src.models.payment import Payment
from src.repositories.outbox import OutboxRepository
from src.repositories.payment import PaymentRepository
from src.schemas.payment import PaymentCreate


class PaymentService:
    """Создаёт и читает платежи, обеспечивая идемпотентность и атомарное сохранение outbox."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payments = PaymentRepository(db)
        self.outbox = OutboxRepository(db)

    async def create(self, data: PaymentCreate, idempotency_key: str) -> Payment:
        values = data.model_dump(exclude={"webhook_url"})
        values["webhook_url"] = str(data.webhook_url)
        values["idempotency_key"] = idempotency_key

        async with self.db.begin():
            payment = await self.payments.create_if_absent(values)
            if payment is None:
                payment = await self.payments.get_matching_request(values)
                if payment is None:
                    raise AppError(
                        "Idempotency key was already used with different payment data",
                        status=409,
                        code="idempotency_conflict",
                    )
            else:
                event_id = uuid4()
                await self.outbox.create({
                    "event_id": event_id,
                    "payment_id": payment.id,
                    "event_type": "payments.new",
                    "payload": {"event_id": str(event_id), "payment_id": payment.id},
                })

        return payment

    async def get(self, payment_id: int) -> Payment:
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise AppError("Payment not found", status=404, code="payment_not_found")
        return payment
