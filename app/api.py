import uuid
from typing import Annotated

from sqlalchemy import select
from fastapi import APIRouter, status, Depends, HTTPException, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db import get_session
from app.models import Payment
from app.schemas import PaymentCreated, PaymentDetail, PaymentCreate


router = APIRouter(prefix='/api/v1/payments', tags=['payments'], dependencies=[Depends(require_api_key)])


def _same_request(p: Payment, body: PaymentCreate) -> bool:
    return (
        p.amount == body.amount
        and p.currency == body.currency
        and p.description == body.description
        and p.metadata_ == body.metadata
        and p.webhook_url == str(body.webhook_url)
    )


async def _existing_or_conflict(session: AsyncSession, key: str, body: PaymentCreate) -> Payment | None:
    existing = (await session.execute(select(Payment).where(Payment.idempotency_key == key))).scalar_one_or_none()
    if existing is not None and not _same_request(existing, body):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Idempotency-Key already used with a different request body'
        )
    return existing


@router.post('', status_code=status.HTTP_202_ACCEPTED, response_model=PaymentCreated)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    session: AsyncSession = Depends(get_session),
):
    existing = await _existing_or_conflict(session, idempotency_key, body)
    if existing:
        return existing

    payment = Payment(
        id=uuid.uuid4(),
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata_=body.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(body.webhook_url),
    )
    session.add(payment)

    #TODO аутбокс

    try:
        await session.commit()
    except IntegrityError:
        # рейс кондишн с одним Idempotency-Key, побеждает первый
        await session.rollback()
        existing = await _existing_or_conflict(session, idempotency_key, body)
        if existing is None:
            raise
        return existing
    return payment


@router.get('/{payment_id}', response_model=PaymentDetail)
async def get_payment(payment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Payment not found')
    return payment
