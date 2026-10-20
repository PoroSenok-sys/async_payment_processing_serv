import asyncio
import logging

from faststream import AckPolicy
from faststream.rabbit import RabbitBroker, RabbitMessage

from src.messaging.topology import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE
from src.schemas.events import PaymentEvent
from src.services.delivery import PaymentDelivery
from src.services.processing import InvalidPaymentEvent, PaymentProcessor

logger = logging.getLogger(__name__)


def register_payment_subscriber(
    broker: RabbitBroker, processor: PaymentProcessor, *, publish_timeout: float = 5
):
    delivery = PaymentDelivery(processor, broker, publish_timeout=publish_timeout)

    @broker.subscriber(
        PAYMENTS_QUEUE,
        PAYMENTS_EXCHANGE,
        ack_policy=AckPolicy.REJECT_ON_ERROR,
    )
    async def handle_payment(event: PaymentEvent, message: RabbitMessage) -> None:
        try:
            acknowledge = await delivery.handle(event, message.headers.get("attempt", 1))
        except InvalidPaymentEvent:
            await message.reject(requeue=False)
        except Exception:
            # Без сохранённого состояния или подтверждения повтора оставляем исходное сообщение.
            # Восстановление инфраструктуры не расходует дополнительную попытку обработки.
            logger.exception("Cannot settle payment event %s; requeuing", event.event_id)
            await asyncio.sleep(1)
            await message.nack(requeue=True)
        else:
            if acknowledge:
                await message.ack()
            else:
                await message.reject(requeue=False)

    return handle_payment
