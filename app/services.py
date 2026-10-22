import asyncio
import logging
import random
import uuid

import httpx
from sqlalchemy import update

from app.config import settings
from app.db import session_factory
from app.models import Payment, PaymentStatus, utcnow

logger = logging.getLogger('payments')


async def emulate_gateway() -> PaymentStatus:
    """Эмуляция внешнего платёжного шлюза - 2-5 сек, 90% успех"""
    await asyncio.sleep(random.uniform(settings.processing_min_sec, settings.processing_max_sec))
    return PaymentStatus.SUCCEEDED if random.random() < settings.success_rate else PaymentStatus.FAILED


async def send_webhook(payment: Payment) -> None:
    payload = {
        'payment_id': str(payment.id),
        'status': payment.status.value,
        'amount': str(payment.amount),
        'currency': payment.currency.value,
        'description': payment.description,
        'metadata': payment.metadata_,
        'created_at': payment.created_at.isoformat(),
        'processed_at': payment.processed_at.isoformat() if payment.processed_at else None,
    }
    async with httpx.AsyncClient(timeout=settings.webhook_timeout_sec) as client:
        response = await client.post(payment.webhook_url, json=payload)
        response.raise_for_status()  # не-2xx => ошибка => retry на уровне сообщения


async def process_payment(payment_id: uuid.UUID) -> None:
    """Идемпотентная обработка - повторный вызов не обрабатывает платёж и не шлёт webhook дважды"""
    async with session_factory() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            raise LookupError(f'payment {payment_id} not found')
        await session.commit()

        if payment.status == PaymentStatus.PENDING:
            new_status = await emulate_gateway()
            await session.execute(
                update(Payment)
                .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
                .values(status=new_status, processed_at=utcnow())
            )
            await session.commit()
            await session.refresh(payment)
            logger.info('payment %s processed: %s', payment_id, payment.status.value)

        if payment.webhook_delivered_at is None:
            await send_webhook(payment)
            payment.webhook_delivered_at = utcnow()
            await session.commit()
            logger.info('webhook for payment %s delivered', payment_id)
