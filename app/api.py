import uuid

from fastapi import APIRouter, status


router = APIRouter(prefix='/api/v1/payments', tags=['payments'])


@router.post('', status_code=status.HTTP_202_ACCEPTED)
async def create_payment():
    return {'payment': 'payment'}


@router.get('/{payment_id}')
async def get_payment(payment_id: uuid.UUID):
    return {'payment': payment_id}
