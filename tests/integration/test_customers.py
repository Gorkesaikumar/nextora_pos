"""Customer domain tests: loyalty, wallet, credit, coupons, events."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from contexts.customers import services
from contexts.customers.exceptions import (
    CouponError,
    CreditLimitExceeded,
    InsufficientPoints,
    InsufficientWalletBalance,
    ValidationError,
)
from contexts.customers.models import (
    Coupon,
    CouponRedemption,
    Customer,
    LoyaltyTier,
    PointsLedger,
    WalletTxType,
)
from shared.infrastructure.events.models import OutboxEvent

pytestmark = pytest.mark.django_db

_phone_seq = iter(range(1, 100000))


def _customer(name="Cust", **kw):
    phone = kw.pop("phone", f"99900{next(_phone_seq):05d}")
    return Customer.objects.create(name=name, phone=phone, **kw)


def _coupon(code="SAVE10", **kw):
    now = timezone.now()
    return Coupon.objects.create(
        code=code,
        discount_value=kw.pop("discount_value", Decimal("10")),
        valid_from=kw.pop("valid_from", now - timedelta(days=1)),
        valid_to=kw.pop("valid_to", now + timedelta(days=30)),
        **kw,
    )


# --- Customer create -------------------------------------------------------
def test_create_customer_validates_and_emits_event(active_tenant):
    customer = services.create_customer(name="Asha", phone="9990001234")
    assert customer.id is not None
    assert OutboxEvent.objects.filter(event_type="CustomerCreated").exists()


def test_create_customer_rejects_bad_phone(active_tenant):
    with pytest.raises(ValidationError):
        services.create_customer(name="Asha", phone="not-a-phone")


def test_gst_customer_requires_state(active_tenant):
    with pytest.raises(ValidationError) as exc:
        services.create_customer(
            name="Acme Corp", phone="9990005555", gstin="27ABCDE1234F1Z5",
        )
    assert "state_code" in exc.value.errors


# --- Loyalty ---------------------------------------------------------------
def test_earn_points_sets_tier_from_lifetime(active_tenant):
    c = _customer()
    services.earn_points(c.id, points=2000)  # default gold threshold = 2000
    c.refresh_from_db()
    assert c.loyalty_points == 2000
    assert c.lifetime_points == 2000
    assert c.loyalty_tier == LoyaltyTier.GOLD


def test_redeeming_points_does_not_demote_tier(active_tenant):
    """ADR-0002 review B3: tier is based on lifetime, not redeemable, points."""
    c = _customer()
    services.earn_points(c.id, points=2000)        # → GOLD
    services.redeem_points(c.id, 1800)             # balance 200, lifetime 2000
    c.refresh_from_db()
    assert c.loyalty_points == 200
    assert c.lifetime_points == 2000
    assert c.loyalty_tier == LoyaltyTier.GOLD       # not demoted


def test_redeem_more_than_balance_is_rejected(active_tenant):
    """ADR-0002 review B1: no silent clamp; ledger never diverges."""
    c = _customer()
    services.earn_points(c.id, points=100)
    with pytest.raises(InsufficientPoints):
        services.redeem_points(c.id, 200)
    c.refresh_from_db()
    assert c.loyalty_points == 100                  # unchanged
    assert PointsLedger.objects.filter(customer=c).count() == 1  # only the earn


def test_earn_points_is_idempotent(active_tenant):
    c = _customer()
    services.earn_points(c.id, points=100, idempotency_key="earn-1")
    services.earn_points(c.id, points=100, idempotency_key="earn-1")  # redelivery
    c.refresh_from_db()
    assert c.loyalty_points == 100
    assert PointsLedger.objects.filter(customer=c).count() == 1


def test_earn_points_from_amount_uses_earn_rate(active_tenant):
    c = _customer()
    program = services.get_loyalty_program()
    program.earn_rate = Decimal("0.1")  # 1 point per 10 currency
    program.save()
    services.earn_points(c.id, amount=Decimal("250"))
    c.refresh_from_db()
    assert c.loyalty_points == 25


# --- Wallet ----------------------------------------------------------------
def test_wallet_deposit_then_pay(active_tenant):
    c = _customer()
    services.adjust_wallet_balance(c.id, Decimal("100"), WalletTxType.DEPOSIT)
    services.adjust_wallet_balance(c.id, Decimal("-40"), WalletTxType.PAYMENT)
    c.refresh_from_db()
    assert c.wallet_balance == Decimal("60.00")


def test_wallet_overdraw_rejected(active_tenant):
    c = _customer()
    services.adjust_wallet_balance(c.id, Decimal("30"), WalletTxType.DEPOSIT)
    with pytest.raises(InsufficientWalletBalance):
        services.adjust_wallet_balance(c.id, Decimal("-50"), WalletTxType.PAYMENT)


def test_wallet_is_idempotent(active_tenant):
    c = _customer()
    services.adjust_wallet_balance(c.id, Decimal("100"), WalletTxType.DEPOSIT, idempotency_key="top-1")
    services.adjust_wallet_balance(c.id, Decimal("100"), WalletTxType.DEPOSIT, idempotency_key="top-1")
    c.refresh_from_db()
    assert c.wallet_balance == Decimal("100.00")


# --- Store credit ----------------------------------------------------------
def test_credit_charge_enforces_limit_and_settle(active_tenant):
    c = _customer(credit_limit=Decimal("1000"))
    inv = uuid.uuid4()
    services.charge_store_credit(c.id, Decimal("600"), inv)
    with pytest.raises(CreditLimitExceeded):
        services.charge_store_credit(c.id, Decimal("600"), uuid.uuid4())
    services.settle_store_credit(c.id, Decimal("300"), inv)
    c.refresh_from_db()
    assert c.outstanding_credit == Decimal("300.00")


# --- Coupons ---------------------------------------------------------------
def test_coupon_redeem_atomic_and_per_customer_cap(active_tenant):
    """ADR-0002 review B7: atomic claim + per-customer limit."""
    coupon = _coupon(per_customer_limit=1, max_uses=100)
    c1, c2 = _customer(), _customer()

    services.redeem_coupon(code=coupon.code, customer_id=c1.id, order_subtotal=Decimal("500"))
    with pytest.raises(CouponError):
        services.redeem_coupon(code=coupon.code, customer_id=c1.id, order_subtotal=Decimal("500"))
    services.redeem_coupon(code=coupon.code, customer_id=c2.id, order_subtotal=Decimal("500"))

    coupon.refresh_from_db()
    assert coupon.current_uses == 2
    assert CouponRedemption.objects.filter(coupon=coupon).count() == 2


def test_coupon_below_min_purchase_rejected(active_tenant):
    coupon = _coupon(min_purchase=Decimal("300"))
    c = _customer()
    with pytest.raises(CouponError):
        services.redeem_coupon(code=coupon.code, customer_id=c.id, order_subtotal=Decimal("100"))


def test_redeem_coupon_is_idempotent(active_tenant):
    coupon = _coupon(per_customer_limit=1)
    c = _customer()
    r1 = services.redeem_coupon(
        code=coupon.code, customer_id=c.id, order_subtotal=Decimal("500"),
        idempotency_key="redeem-1",
    )
    r2 = services.redeem_coupon(
        code=coupon.code, customer_id=c.id, order_subtotal=Decimal("500"),
        idempotency_key="redeem-1",
    )
    assert r1.id == r2.id
    coupon.refresh_from_db()
    assert coupon.current_uses == 1  # not double-counted
