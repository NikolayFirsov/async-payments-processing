from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType, RabbitQueue

from app.config import settings


EXCHANGE_NAME = 'payments'
DEAD_LETTER_EXCHANGE_NAME = 'payments.dlx'
MAIN_ROUTING_KEY = 'payments.new'
DEAD_LETTER_ROUTING_KEY = 'payments.new.dlq'

broker = RabbitBroker(settings.rabbitmq_url)

main_exchange = RabbitExchange(EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)
dead_letter_exchange = RabbitExchange(DEAD_LETTER_EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)

main_queue = RabbitQueue(
    'payments.new',
    durable=True,
    routing_key=MAIN_ROUTING_KEY,
    arguments={
        'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE_NAME,
        'x-dead-letter-routing-key': DEAD_LETTER_ROUTING_KEY,
    },
)

dead_letter_queue = RabbitQueue('payments.new.dlq', durable=True, routing_key=DEAD_LETTER_ROUTING_KEY)


def get_retry_routing_key(attempt: int) -> str:
    return f'payments.new.retry.{attempt}'


def retry_queue(attempt: int) -> RabbitQueue:
    """Создает retry очередь для попытки attempt с экспоненциальной задержкой"""
    delay_ms = settings.retry_base_delay_sec * (2 ** (attempt - 1)) * 1000

    routing_key = get_retry_routing_key(attempt)

    return RabbitQueue(
        get_retry_routing_key(attempt),
        durable=True,
        routing_key=routing_key,
        arguments={
            'x-message-ttl': delay_ms,
            'x-dead-letter-exchange': EXCHANGE_NAME,
            'x-dead-letter-routing-key': MAIN_ROUTING_KEY,
        },
    )


async def declare_configuration(r_broker: RabbitBroker) -> None:
    """Объявляет все обменники, очереди и биндинги"""
    main_exchange_instance = await r_broker.declare_exchange(main_exchange)
    dead_letter_exchange_instance = await r_broker.declare_exchange(dead_letter_exchange)

    main_queue_instance = await r_broker.declare_queue(main_queue)
    await main_queue_instance.bind(main_exchange_instance, routing_key=MAIN_ROUTING_KEY)

    for attempt in range(1, settings.max_attempts):  # retry очереди для попыток 1 - max-1
        retry_queue_instance = await r_broker.declare_queue(retry_queue(attempt))
        await retry_queue_instance.bind(main_exchange_instance, routing_key=get_retry_routing_key(attempt))

    dead_letter_queue_instance = await r_broker.declare_queue(dead_letter_queue)
    await dead_letter_queue_instance.bind(dead_letter_exchange_instance, routing_key=DEAD_LETTER_ROUTING_KEY)
