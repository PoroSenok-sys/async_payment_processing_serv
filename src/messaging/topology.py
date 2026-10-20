from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

PAYMENTS_EXCHANGE = RabbitExchange("payments", durable=True)
RETRY_EXCHANGE = RabbitExchange("payments.retry", durable=True)
DEAD_LETTER_EXCHANGE = RabbitExchange("payments.dlx", durable=True)

DEAD_LETTER_QUEUE = RabbitQueue("payments.dlq", durable=True, routing_key="payments.dead")
PAYMENTS_QUEUE = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name,
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE.routing(),
    },
)
RETRY_QUEUES = tuple(
    RabbitQueue(
        f"payments.retry.{seconds}s",
        durable=True,
        arguments={
            "x-message-ttl": seconds * 1000,
            "x-dead-letter-exchange": PAYMENTS_EXCHANGE.name,
            "x-dead-letter-routing-key": PAYMENTS_QUEUE.routing(),
        },
    )
    for seconds in (1, 2)
)


async def declare_topology(broker: RabbitBroker) -> None:
    """Объявляет сохраняемые обменники, очереди и привязки; допускает повтор с теми же настройками."""
    for exchange in (PAYMENTS_EXCHANGE, RETRY_EXCHANGE, DEAD_LETTER_EXCHANGE):
        await broker.declare_exchange(exchange)

    for queue, exchange in (
        (DEAD_LETTER_QUEUE, DEAD_LETTER_EXCHANGE),
        (PAYMENTS_QUEUE, PAYMENTS_EXCHANGE),
        *((queue, RETRY_EXCHANGE) for queue in RETRY_QUEUES),
    ):
        declared = await broker.declare_queue(queue)
        await declared.bind(exchange.name, routing_key=queue.routing())
