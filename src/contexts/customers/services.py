"""Customer domain services.

Value accounts (wallet, store credit, loyalty points) are ledger-backed: each
mutation locks the customer row, updates the projection, and appends an
immutable ledger entry. All order-driven postings accept an ``idempotency_key``
so a redelivered/retried event never double-posts. Engagement events are
published in the same transaction via the outbox.
"""
import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from .events import (
    publish_coupon_redeemed,
    publish_credit_charged,
    publish_credit_settled,
    publish_customer_created,
    publish_points_earned,
    publish_points_redeemed,
    publish_wallet_spent,
    publish_wallet_topped_up,
)
from .exceptions import (
    CouponError,
    CreditLimitExceeded,
    CustomerNotFound,
    InsufficientPoints,
    InsufficientWalletBalance,
    ValidationError,
)
from .models import (
    Coupon,
    CouponRedemption,
    CreditLedger,
    CreditLedgerType,
    Customer,
    LoyaltyProgram,
    PointsLedger,
    WalletTransaction,
)
from .validation import validate_customer

logger = logging.getLogger(__name__)


# --- Helpers ---------------------------------------------------------------
def _lock_customer(customer_id: UUID) -> Customer:
    try:
        return Customer.objects.select_for_update().get(id=customer_id)
    except Customer.DoesNotExist as exc:
        raise CustomerNotFound(str(customer_id)) from exc


def _get_customer(customer_id: UUID) -> Customer:
    try:
        return Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist as exc:
        raise CustomerNotFound(str(customer_id)) from exc


def get_loyalty_program() -> LoyaltyProgram:
    """The tenant's loyalty config, created with sensible defaults on first use."""
    program, _ = LoyaltyProgram.objects.get_or_create()
    return program


def _already_posted(model, idempotency_key: str) -> bool:
    return bool(idempotency_key) and model.objects.filter(
        idempotency_key=idempotency_key
    ).exists()


# --- Customer --------------------------------------------------------------
@transaction.atomic
def create_customer(*, name: str, phone: str, **fields) -> Customer:
    validate_customer({"name": name, "phone": phone, **fields})
    customer = Customer(name=name, phone=phone, **fields)
    customer.save()
    publish_customer_created(customer.id, customer.phone)
    return customer


# --- Loyalty ---------------------------------------------------------------
@transaction.atomic
def earn_points(
    customer_id: UUID,
    *,
    amount: Decimal | None = None,
    points: int | None = None,
    reason: str = "purchase",
    order_id: UUID | None = None,
    idempotency_key: str = "",
) -> Customer:
    """Earn points from a spend ``amount`` (via the earn rate) or an explicit
    ``points`` grant. Increases both the redeemable balance and lifetime points;
    tier is recomputed from **lifetime** points so redemption never demotes."""
    if _already_posted(PointsLedger, idempotency_key):
        return _get_customer(customer_id)

    customer = _lock_customer(customer_id)
    program = get_loyalty_program()

    if points is None:
        if amount is None:
            raise ValidationError({"points": "Provide either points or amount."})
        points = int(Decimal(str(amount)) * program.earn_rate)
    if points <= 0:
        return customer

    customer.loyalty_points += points
    customer.lifetime_points += points
    customer.loyalty_tier = program.tier_for(customer.lifetime_points)
    customer.save(update_fields=[
        "loyalty_points", "lifetime_points", "loyalty_tier", "updated_at"
    ])
    PointsLedger.objects.create(
        customer=customer, points=points, reason=reason,
        order_id=order_id, idempotency_key=idempotency_key,
    )
    publish_points_earned(customer.id, points, customer.loyalty_tier, order_id)
    return customer


@transaction.atomic
def redeem_points(
    customer_id: UUID,
    points: int,
    *,
    reason: str = "redemption",
    order_id: UUID | None = None,
    idempotency_key: str = "",
) -> Customer:
    """Redeem points. Rejects redeeming more than the balance (never clamps), and
    reduces only the redeemable balance — lifetime points (the tier basis) stay."""
    if points <= 0:
        raise ValidationError({"points": "Redemption must be positive."})
    if _already_posted(PointsLedger, idempotency_key):
        return _get_customer(customer_id)

    customer = _lock_customer(customer_id)
    if customer.loyalty_points < points:
        raise InsufficientPoints(customer.loyalty_points, points)

    customer.loyalty_points -= points
    customer.save(update_fields=["loyalty_points", "updated_at"])
    PointsLedger.objects.create(
        customer=customer, points=-points, reason=reason,
        order_id=order_id, idempotency_key=idempotency_key,
    )
    publish_points_redeemed(customer.id, points, order_id)
    return customer


# --- Wallet ----------------------------------------------------------------
@transaction.atomic
def adjust_wallet_balance(
    customer_id: UUID,
    amount: Decimal,
    tx_type: str,
    order_id: UUID | None = None,
    idempotency_key: str = "",
) -> Customer:
    """Increment (deposit/refund) or decrement (payment) the wallet under a lock.
    A spend that would overdraw raises ``InsufficientWalletBalance``."""
    if _already_posted(WalletTransaction, idempotency_key):
        return _get_customer(customer_id)

    customer = _lock_customer(customer_id)
    new_balance = customer.wallet_balance + amount
    if new_balance < Decimal("0.00"):
        raise InsufficientWalletBalance(customer.wallet_balance, abs(amount))

    customer.wallet_balance = new_balance
    customer.save(update_fields=["wallet_balance", "updated_at"])
    WalletTransaction.objects.create(
        customer=customer, amount=amount, tx_type=tx_type,
        order_id=order_id, idempotency_key=idempotency_key,
    )
    if amount >= 0:
        publish_wallet_topped_up(customer.id, amount, new_balance)
    else:
        publish_wallet_spent(customer.id, -amount, new_balance, order_id)
    return customer


# --- Store credit ----------------------------------------------------------
@transaction.atomic
def charge_store_credit(
    customer_id: UUID, amount: Decimal, invoice_id: UUID, *, idempotency_key: str = ""
) -> Customer:
    if _already_posted(CreditLedger, idempotency_key):
        return _get_customer(customer_id)

    customer = _lock_customer(customer_id)
    new_outstanding = customer.outstanding_credit + amount
    if new_outstanding > customer.credit_limit:
        raise CreditLimitExceeded(customer.credit_limit, new_outstanding)

    customer.outstanding_credit = new_outstanding
    customer.save(update_fields=["outstanding_credit", "updated_at"])
    CreditLedger.objects.create(
        customer=customer, amount=amount, ledger_type=CreditLedgerType.CHARGE,
        invoice_id=invoice_id, idempotency_key=idempotency_key,
    )
    publish_credit_charged(customer.id, amount, new_outstanding, invoice_id)
    return customer


@transaction.atomic
def settle_store_credit(
    customer_id: UUID, amount: Decimal, invoice_id: UUID, *, idempotency_key: str = ""
) -> Customer:
    if _already_posted(CreditLedger, idempotency_key):
        return _get_customer(customer_id)

    customer = _lock_customer(customer_id)
    customer.outstanding_credit = max(Decimal("0.00"), customer.outstanding_credit - amount)
    customer.save(update_fields=["outstanding_credit", "updated_at"])
    CreditLedger.objects.create(
        customer=customer, amount=-amount, ledger_type=CreditLedgerType.SETTLEMENT,
        invoice_id=invoice_id, idempotency_key=idempotency_key,
    )
    publish_credit_settled(customer.id, amount, customer.outstanding_credit, invoice_id)
    return customer


# --- Coupons ---------------------------------------------------------------
def validate_coupon(coupon_code: str, tenant_id: UUID, order_subtotal: Decimal) -> Coupon:
    """Read-only validation (date window, global cap, minimum spend).

    Uses the tenant-scoped manager (the active tenant is bound in context), so it
    no longer reaches across tenants via ``all_objects``.
    """
    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
    except Coupon.DoesNotExist as exc:
        raise CouponError("Coupon code does not exist or is currently inactive.") from exc
    _assert_coupon_usable(coupon, order_subtotal)
    return coupon


def _assert_coupon_usable(coupon: Coupon, order_subtotal: Decimal) -> None:
    now = timezone.now()
    if not (coupon.valid_from <= now <= coupon.valid_to):
        raise CouponError("Coupon has expired or is not yet valid.")
    if coupon.current_uses >= coupon.max_uses:
        raise CouponError("Coupon has reached its maximum usage limit.")
    if order_subtotal < coupon.min_purchase:
        raise CouponError(
            f"Order subtotal does not meet the minimum purchase of {coupon.min_purchase}."
        )


@transaction.atomic
def redeem_coupon(
    *,
    code: str,
    customer_id: UUID,
    order_subtotal: Decimal,
    order_id: UUID | None = None,
    idempotency_key: str = "",
) -> CouponRedemption:
    """Atomically claim a coupon: lock it, re-validate, enforce the per-customer
    cap, increment usage and record the redemption — replacing the previous
    non-atomic ``current_uses`` check that allowed over-redemption."""
    if _already_posted(CouponRedemption, idempotency_key):
        return CouponRedemption.objects.get(idempotency_key=idempotency_key)

    try:
        coupon = Coupon.objects.select_for_update().get(code=code, is_active=True)
    except Coupon.DoesNotExist as exc:
        raise CouponError("Coupon code does not exist or is currently inactive.") from exc

    _assert_coupon_usable(coupon, order_subtotal)

    used_by_customer = CouponRedemption.objects.filter(
        coupon=coupon, customer_id=customer_id
    ).count()
    if used_by_customer >= coupon.per_customer_limit:
        raise CouponError("Coupon already redeemed the maximum number of times by this customer.")

    coupon.current_uses += 1
    coupon.save(update_fields=["current_uses", "updated_at"])

    redemption = CouponRedemption.objects.create(
        coupon=coupon, customer_id=customer_id, order_id=order_id,
        idempotency_key=idempotency_key,
    )
    publish_coupon_redeemed(customer_id, coupon.id, coupon.code, order_id)
    return redemption
