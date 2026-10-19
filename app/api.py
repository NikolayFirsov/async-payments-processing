import uuid
from typing import Annotated

from fastapi import APIRouter, status, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db import get_session
from app.models import Payment
from app.schemas import PaymentCreated, PaymentDetail, PaymentCreate


router = APIRouter(prefix='/api/v1/payments', tags=['payments'], dependencies=[Depends(require_api_key)])


@router.post('', status_code=status.HTTP_202_ACCEPTED, response_model=PaymentCreated)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    session: AsyncSession = Depends(get_session),
):
    #TODO check for existing
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

    await session.commit()

    return payment


@router.get('/{payment_id}', response_model=PaymentDetail)
async def get_payment(payment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Payment not found')
    return payment
