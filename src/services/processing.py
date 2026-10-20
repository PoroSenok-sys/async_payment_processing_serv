import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.enums import PaymentStatus
from src.repositories.outbox import OutboxRepository
from src.repositories.payment import PaymentRepository
from src.schemas.events import PaymentEvent, PaymentWebhook
from src.services.gateway import EmulatedGateway
from src.services.webhook import WebhookSender

logger = logging.getLogger(__name__)


class InvalidPaymentEvent(ValueError):
    """Событие не соответствует существующему платежу и его записи outbox."""


class PaymentProcessor:
    """Сохраняет результат платежа и отправляет webhook без повторного проведения."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        gateway: EmulatedGateway,
        webhook: WebhookSender,
    ) -> None:
        self.sessions = sessions
        self.gateway = gateway
        self.webhook = webhook

    async def process(self, event: PaymentEvent) -> None:
        url, notification = await self._complete_payment(event)
        # Перед HTTP-запросом результат уже сохранён, а блокировка строки снята.
        await self.webhook.send(url, notification)
        logger.info("Delivered webhook %s for payment %s", event.event_id, event.payment_id)

    async def _complete_payment(self, event: PaymentEvent) -> tuple[str, PaymentWebhook]:
        async with self.sessions() as session, session.begin():
            stored_event = await OutboxRepository(session).get_payment_event(
                event.event_id, event.payment_id
            )
            if stored_event is None:
                raise InvalidPaymentEvent("Unknown payment event")

            payment = await PaymentRepository(session).get_for_update(event.payment_id)
            if payment is None:
                raise InvalidPaymentEvent("Payment not found")

            if payment.status == PaymentStatus.PENDING:
                # Обрабатываем параллельные дубли последовательно во время локальной эмуляции.
                # Эмулятор не выполняет сетевых запросов внутри транзакции.
                result = await self.gateway.charge(payment)
                if result not in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
                    raise ValueError("Gateway must return a final payment status")
                payment.status = result
                payment.processed_at = datetime.now(timezone.utc)
                logger.info("Payment %s completed with status %s", payment.id, result)

            notification = PaymentWebhook(
                event_id=stored_event.event_id,
                payment_id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                status=payment.status,
                processed_at=payment.processed_at,
            )
            url = payment.webhook_url

        return url, notification
