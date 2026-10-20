from faststream.rabbit import Channel, RabbitBroker

from src.core.config import settings


def create_broker(url: str | None = None) -> RabbitBroker:
    return RabbitBroker(
        url or settings.rabbitmq_url,
        default_channel=Channel(prefetch_count=1, publisher_confirms=True, on_return_raises=True),
        timeout=settings.RABBITMQ_CONNECT_TIMEOUT,
        reconnect_interval=1,
        fail_fast=False,
        app_id=settings.SERVICE_NAME,
    )


broker = create_broker()
