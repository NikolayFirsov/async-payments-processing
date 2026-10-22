import asyncio
import logging

from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from app.broker import EXCHANGE_NAME, MAIN_ROUTING_KEY
from app.config import settings
from app.db import session_factory
from app.models import Outbox, utcnow

logger = logging.getLogger('outbox')


async def publish_batch(broker: RabbitBroker) -> int:
    async with session_factory() as session, session.begin():
        rows = (
            (
                await session.execute(
                    select(Outbox)
                    .where(Outbox.published_at.is_(None))
                    .order_by(Outbox.id)
                    .limit(settings.outbox_batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            await broker.publish(
                row.payload,
                exchange=EXCHANGE_NAME,
                routing_key=MAIN_ROUTING_KEY,
                persist=True,
                message_id=str(row.id),
                headers={'x-attempt': 1},
            )
            row.published_at = utcnow()
        return len(rows)


async def relay_loop(broker: RabbitBroker, stop: asyncio.Event) -> None:
    logger.info('outbox relay started')
    while not stop.is_set():
        published = 0
        try:
            published = await publish_batch(broker)
        except Exception:
            logger.exception('outbox publish failed, will retry')
        if published == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.outbox_poll_interval_sec)
            except asyncio.TimeoutError:
                pass
    logger.info('outbox relay stopped')
