import uuid
from typing import Any
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field, AnyHttpUrl, ConfigDict, AliasChoices

from app.models import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(title='Сумма платежа', gt=0, max_digits=18, decimal_places=2)
    currency: Currency = Field(title='Валюта платежа', description='Валюта платежа: RUB, USD или EUR')
    description: str = Field(title='Описание платежа', min_length=1, max_length=1000)
    metadata: dict[str, Any] = Field(title='Метаданные', default_factory=dict)
    webhook_url: AnyHttpUrl = Field(title='Webhook URL')


class PaymentCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID = Field(
        title='ID платежа',
        validation_alias=AliasChoices('id', 'payment_id'),
    )
    status: PaymentStatus = Field(title='Статус платежа')
    created_at: datetime = Field(title='Дата создания платежа')


class PaymentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_id: uuid.UUID = Field(
        title='ID платежа',
        validation_alias=AliasChoices('id', 'payment_id'),
    )
    amount: Decimal = Field(title='Сумма платежа')
    currency: Currency = Field(title='Валюта платежа', description='Валюта платежа: RUB, USD или EUR')
    description: str = Field(title='Описание платежа')
    metadata: dict[str, Any] = Field(
        title='Метаданные',
        validation_alias=AliasChoices('metadata_', 'metadata'),
    )
    status: PaymentStatus = Field(title='Статус платежа')
    idempotency_key: str = Field(title='Idempotency key')
    webhook_url: str = Field(title='Webhook URL')
    created_at: datetime = Field(title='Дата создания платежа')
    processed_at: datetime | None = Field(title='Дата обработки платежа', default=None)
