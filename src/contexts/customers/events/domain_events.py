"""Customer domain event definitions.

Each extends the shared :class:`DomainEvent` (defaulted base fields → subclass
fields must default too). Payloads are JSON-safe: ids are serialised by the
dispatcher, money is carried as strings.
"""
import uuid
from dataclasses import dataclass

from shared.domain.events import DomainEvent


@dataclass(frozen=True)
class CustomerCreated(DomainEvent):
    customer_id: uuid.UUID | None = None
    phone: str = ""


@dataclass(frozen=True)
class PointsEarned(DomainEvent):
    customer_id: uuid.UUID | None = None
    points: int = 0
    new_tier: str = ""
    order_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PointsRedeemed(DomainEvent):
    customer_id: uuid.UUID | None = None
    points: int = 0
    order_id: uuid.UUID | None = None


@dataclass(frozen=True)
class WalletToppedUp(DomainEvent):
    customer_id: uuid.UUID | None = None
    amount: str = "0"
    balance: str = "0"


@dataclass(frozen=True)
class WalletSpent(DomainEvent):
    customer_id: uuid.UUID | None = None
    amount: str = "0"
    balance: str = "0"
    order_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreditCharged(DomainEvent):
    customer_id: uuid.UUID | None = None
    amount: str = "0"
    outstanding: str = "0"
    invoice_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreditSettled(DomainEvent):
    customer_id: uuid.UUID | None = None
    amount: str = "0"
    outstanding: str = "0"
    invoice_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CouponRedeemed(DomainEvent):
    customer_id: uuid.UUID | None = None
    coupon_id: uuid.UUID | None = None
    code: str = ""
    order_id: uuid.UUID | None = None
