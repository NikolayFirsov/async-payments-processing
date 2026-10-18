import enum
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Numeric, Text, String, DateTime, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Currency(str, enum.Enum):
    RUB = 'RUB'
    USD = 'USD'
    EUR = 'EUR'


class PaymentStatus(str, enum.Enum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(
            Currency,
            native_enum=False,
            length=3,
            values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    metadata_: Mapped[dict] = mapped_column('metadata', JSONB, nullable=False, default=dict)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
