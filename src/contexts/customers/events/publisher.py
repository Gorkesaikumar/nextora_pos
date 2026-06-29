"""Publish customer events through the shared transactional outbox.

Stamps the active tenant and dispatches in-transaction, so an engagement event
never diverges from the value-account write that produced it.
"""
import uuid
from decimal import Decimal
from typing import Optional

from shared.domain.events import DomainEvent
from shared.infrastructure.events.dispatcher import dispatch
from shared.tenancy.context import get_current_tenant

from .domain_events import (
    CouponRedeemed,
    CreditCharged,
    CreditSettled,
    CustomerCreated,
    PointsEarned,
    PointsRedeemed,
    WalletSpent,
    WalletToppedUp,
)


def _publish(event: DomainEvent) -> None:
    dispatch(event)


def publish_customer_created(customer_id: uuid.UUID, phone: str) -> None:
    _publish(CustomerCreated(
        tenant_id=get_current_tenant(), customer_id=customer_id, phone=phone
    ))


def publish_points_earned(
    customer_id: uuid.UUID, points: int, new_tier: str, order_id: Optional[uuid.UUID]
) -> None:
    _publish(PointsEarned(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        points=points, new_tier=new_tier, order_id=order_id,
    ))


def publish_points_redeemed(
    customer_id: uuid.UUID, points: int, order_id: Optional[uuid.UUID]
) -> None:
    _publish(PointsRedeemed(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        points=points, order_id=order_id,
    ))


def publish_wallet_topped_up(customer_id: uuid.UUID, amount: Decimal, balance: Decimal) -> None:
    _publish(WalletToppedUp(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        amount=str(amount), balance=str(balance),
    ))


def publish_wallet_spent(
    customer_id: uuid.UUID, amount: Decimal, balance: Decimal, order_id: Optional[uuid.UUID]
) -> None:
    _publish(WalletSpent(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        amount=str(amount), balance=str(balance), order_id=order_id,
    ))


def publish_credit_charged(
    customer_id: uuid.UUID, amount: Decimal, outstanding: Decimal, invoice_id: Optional[uuid.UUID]
) -> None:
    _publish(CreditCharged(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        amount=str(amount), outstanding=str(outstanding), invoice_id=invoice_id,
    ))


def publish_credit_settled(
    customer_id: uuid.UUID, amount: Decimal, outstanding: Decimal, invoice_id: Optional[uuid.UUID]
) -> None:
    _publish(CreditSettled(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        amount=str(amount), outstanding=str(outstanding), invoice_id=invoice_id,
    ))


def publish_coupon_redeemed(
    customer_id: uuid.UUID, coupon_id: uuid.UUID, code: str, order_id: Optional[uuid.UUID]
) -> None:
    _publish(CouponRedeemed(
        tenant_id=get_current_tenant(), customer_id=customer_id,
        coupon_id=coupon_id, code=code, order_id=order_id,
    ))
