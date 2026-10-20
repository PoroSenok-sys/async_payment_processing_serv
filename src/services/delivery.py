import asyncio
import logging
from datetime import datetime, timedelta, timezone

from faststream.rabbit import RabbitBroker

from src.messaging.topology import RETRY_EXCHANGE, RETRY_QUEUES
from src.models.outbox import Outbox
from src.repositories.outbox import OutboxRepository
from src.schemas.events import PaymentEvent
from src.services.processing import InvalidPaymentEvent, PaymentProcessor

logger = logging.getLogger(__name__)


class DeliveryBusy(RuntimeError):
    """Другой обработчик уже выполняет это событие."""


class PaymentDelivery:
    """Управляет тремя попытками обработки, повторной доставкой и направлением в DLQ."""

    def __init__(self, processor: PaymentProcessor, broker: RabbitBroker, publish_timeout: float = 5) -> None:
        self.processor = processor
        self.sessions = processor.sessions
        self.broker = broker
        self.publish_timeout = publish_timeout

    async def handle(self, event: PaymentEvent, attempt: int) -> bool:
        """Возвращает True для подтверждения, False для DLQ; ошибки БД и связи требуют возврата."""
        if type(attempt) is not int or not 1 <= attempt <= 3:
            raise InvalidPaymentEvent("Invalid attempt header")

        async with self.sessions() as guard, guard.begin():
            repository = OutboxRepository(guard)
            state = await repository.get_payment_event(event.event_id, event.payment_id)
            if state is None:
                raise InvalidPaymentEvent("Unknown payment event")
            if not await repository.try_lock_consumer(state.event_id):
                raise DeliveryBusy("Payment event is already being processed")
            await guard.refresh(state)

            if state.consumer_state == "completed":
                return True
            if state.consumer_state == "dead":
                return False
            if state.consumer_state == "processing":
                # Блокировка свободна, но предыдущая попытка не отмечена завершённой.
                # При сбое начатая и сохранённая до обработки попытка считается потраченной.
                state = await self._fail(event, "Interrupted consumer attempt")

            if state.consumer_state == "retry":
                ready = datetime.now(timezone.utc) >= state.consumer_next_attempt_at
                if attempt != state.consumer_attempts + 1 or not ready:
                    return await self._route_failure(state)
            elif state.consumer_state == "dead":
                return False
            elif attempt != 1:
                raise InvalidPaymentEvent("Unexpected initial attempt")

            await self._start(event)
            try:
                await self.processor.process(event)
            except InvalidPaymentEvent as exc:
                state = await self._fail(event, f"{type(exc).__name__}: {exc}", permanent=True)
            except Exception as exc:
                state = await self._fail(event, f"{type(exc).__name__}: {exc}")
            else:
                await self._complete(event)
                return True

            return await self._route_failure(state)

    async def _start(self, event: PaymentEvent) -> None:
        async with self.sessions() as session, session.begin():
            state = await OutboxRepository(session).get_payment_event(
                event.event_id, event.payment_id, lock=True
            )
            state.consumer_attempts += 1
            state.consumer_state = "processing"
            state.consumer_next_attempt_at = None

    async def _complete(self, event: PaymentEvent) -> None:
        async with self.sessions() as session, session.begin():
            state = await OutboxRepository(session).get_payment_event(
                event.event_id, event.payment_id, lock=True
            )
            state.consumer_state = "completed"
            state.consumer_last_error = None

    async def _fail(self, event: PaymentEvent, error: str, *, permanent: bool = False) -> Outbox:
        async with self.sessions() as session, session.begin():
            state = await OutboxRepository(session).get_payment_event(
                event.event_id, event.payment_id, lock=True
            )
            state.consumer_last_error = error
            if permanent or state.consumer_attempts >= 3:
                state.consumer_state = "dead"
                state.consumer_next_attempt_at = None
            else:
                state.consumer_state = "retry"
                delay = 2 ** (state.consumer_attempts - 1)
                state.consumer_next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        logger.warning("Payment event %s attempt %s: %s", event.event_id, state.consumer_attempts, error)
        return state

    async def _route_failure(self, state: Outbox) -> bool:
        if state.consumer_state == "dead":
            return False
        retry_queue = RETRY_QUEUES[state.consumer_attempts - 1]
        async with asyncio.timeout(self.publish_timeout):
            confirmation = await self.broker.publish(
                state.payload,
                exchange=RETRY_EXCHANGE,
                routing_key=retry_queue.routing(),
                persist=True,
                mandatory=True,
                timeout=self.publish_timeout,
                message_id=str(state.event_id),
                correlation_id=str(state.payment_id),
                message_type=state.event_type,
                headers={"attempt": state.consumer_attempts + 1},
                timestamp=state.created_at,
            )
            if not confirmation:
                raise RuntimeError("RabbitMQ did not confirm retry publication")
        return True
