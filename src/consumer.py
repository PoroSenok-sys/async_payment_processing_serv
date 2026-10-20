from contextlib import asynccontextmanager

from faststream import FastStream

from src.core.config import settings
from src.core.lifespan import lifespan
from src.database import SessionLocal
from src.messaging.broker import broker
from src.messaging.payments import register_payment_subscriber
from src.messaging.topology import declare_topology
from src.services.gateway import EmulatedGateway
from src.services.outbox import OutboxPublisher
from src.services.processing import PaymentProcessor
from src.services.webhook import WebhookSender

publisher = OutboxPublisher(
    SessionLocal,
    broker,
    poll_interval=settings.OUTBOX_POLL_INTERVAL,
    batch_size=settings.OUTBOX_BATCH_SIZE,
    publish_timeout=settings.RABBITMQ_PUBLISH_TIMEOUT,
)
processor = PaymentProcessor(
    SessionLocal,
    EmulatedGateway(),
    WebhookSender(timeout=settings.WEBHOOK_TIMEOUT),
)
register_payment_subscriber(broker, processor, publish_timeout=settings.RABBITMQ_PUBLISH_TIMEOUT)


@asynccontextmanager
async def consumer_lifespan():
    async with lifespan():
        try:
            yield
        finally:
            await publisher.stop()


app = FastStream(broker, lifespan=consumer_lifespan)


@app.on_startup
async def prepare_broker():
    # Объявляем DLX и очереди повторов до начала получения накопившихся сообщений.
    await broker.connect()
    await declare_topology(broker)


@app.after_startup
async def start_publisher():
    publisher.start()


@app.on_shutdown
async def stop_publisher():
    await publisher.stop()
