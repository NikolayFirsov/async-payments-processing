import logging

from faststream import FastStream
from faststream.rabbit import RabbitMessage

from app.broker import (
    broker, declare_configuration, main_queue, main_exchange, EXCHANGE_NAME, get_retry_routing_key, 
    DEAD_LETTER_EXCHANGE_NAME, DEAD_LETTER_ROUTING_KEY
)
from app.schemas import PaymentEvent
from app.services import process_payment
from app.config import settings


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('consumer')


app = FastStream(broker)


@app.after_startup
async def _declare() -> None:
    await declare_configuration(broker)


@broker.subscriber(main_queue, main_exchange)
async def handle_new_payment(event: PaymentEvent, message: RabbitMessage) -> None:
    attempt = int((message.headers or {}).get('x-attempt', 1))
    try:
        await process_payment(event.payment_id)
    except Exception as exc:
        logger.exception(
            'attempt %d/%d failed for payment %s',
            attempt,
            settings.max_attempts,
            event.payment_id
        )
        body = event.model_dump(mode='json')
        if attempt < settings.max_attempts:
            await broker.publish(
                body,
                exchange=EXCHANGE_NAME,
                routing_key=get_retry_routing_key(attempt),
                headers={'x-attempt': attempt + 1},
                persist=True,
            )
        else:
            logger.error('payment %s moved to DLQ after %d attempts', event.payment_id, attempt)
            await broker.publish(
                body,
                exchange=DEAD_LETTER_EXCHANGE_NAME,
                routing_key=DEAD_LETTER_ROUTING_KEY,
                headers={'x-attempt': attempt, 'x-error': repr(exc)[:500]},
                persist=True,
            )
