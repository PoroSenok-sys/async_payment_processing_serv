import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone

from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.messaging.topology import PAYMENTS_EXCHANGE
from src.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher:
    """Публикует сохранённые события с доставкой хотя бы один раз и ограничением ожидания."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        broker: RabbitBroker,
        *,
        poll_interval: float = 1,
        batch_size: int = 100,
        publish_timeout: float = 5,
    ) -> None:
        self.sessions = sessions
        self.broker = broker
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.publish_timeout = publish_timeout
        self._task: asyncio.Task | None = None

    async def publish_one(self) -> bool:
        # На время ограниченного ожидания подтверждения брокера блокируется одна строка.
        # Отмена или сбой откатывает изменения и позволяет повторить публикацию.
        async with self.sessions() as session, session.begin():
            event = await OutboxRepository(session).get_next_ready()
            if event is None:
                return False

            event.attempts += 1
            try:
                async with asyncio.timeout(self.publish_timeout):
                    confirmation = await self.broker.publish(
                        event.payload,
                        exchange=PAYMENTS_EXCHANGE,
                        routing_key=event.event_type,
                        persist=True,
                        mandatory=True,
                        timeout=self.publish_timeout,
                        message_id=str(event.event_id),
                        correlation_id=str(event.payment_id),
                        message_type=event.event_type,
                        headers={"attempt": 1},
                        timestamp=event.created_at,
                    )
                    # При подтверждениях и on_return_raises клиент возвращает Ack либо
                    # выбрасывает исключение при Nack, Reject или отсутствии маршрута. None недостаточно.
                    if not confirmation:
                        raise RuntimeError("RabbitMQ did not confirm publication")
            except Exception as exc:
                event.last_error = f"{type(exc).__name__}: {exc}"
                delay = min(2 ** min(event.attempts - 1, 6), 60)
                event.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                logger.warning("Outbox event %s: %s", event.event_id, event.last_error)
            else:
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                logger.info("Published outbox event %s for payment %s", event.event_id, event.payment_id)

        return True

    async def publish_batch(self) -> int:
        processed = 0
        for _ in range(self.batch_size):
            if not await self.publish_one():
                break
            processed += 1
        return processed

    async def run(self) -> None:
        while True:
            try:
                processed = await self.publish_batch()
            except Exception:
                # Ошибка БД или фиксации транзакции не должна незаметно остановить фоновую задачу.
                logger.exception("Outbox publisher cycle failed")
                processed = 0
            if processed < self.batch_size:
                await asyncio.sleep(self.poll_interval)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(), name="outbox-publisher")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
