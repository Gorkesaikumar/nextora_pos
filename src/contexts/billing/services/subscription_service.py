"""Subscription lifecycle commands: create, change plan, cancel."""
import uuid
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from contexts.billing.domain.enums import SubscriptionStatus
from contexts.billing.domain.periods import add_interval
from contexts.billing.exceptions import (
    ActiveSubscriptionExists,
    NoActiveSubscription,
    PlanNotFound,
    PriceNotFound,
)
from contexts.billing.models import Plan, Subscription, SubscriptionCoupon, CouponUsage
from contexts.billing.services import entitlements, invoice_service
from shared.tenancy import tenant_scope


def _plan_and_price(plan_code: str, interval: str):
    try:
        plan = Plan.objects.get(code=plan_code, is_active=True)
    except Plan.DoesNotExist as exc:
        raise PlanNotFound(plan_code) from exc
    price = plan.prices.filter(interval=interval).first()
    amount = plan.sale_price if plan.sale_price > 0 else plan.original_price
    currency = plan.currency or "INR"
    if price is not None:
        amount = price.amount
        currency = price.currency
    elif amount <= 0 and not plan.prices.exists():
        # Fallback if amount is 0 and no prices defined
        amount = 0
    elif price is None and not (amount >= 0):
        raise PriceNotFound(f"{plan_code}/{interval}")
    return plan, amount, currency


def create_subscription(
    tenant_id: uuid.UUID,
    plan_code: str,
    interval: str,
    now: datetime | None = None,
    coupon_code: str | None = None,
) -> Subscription:
    """Start a subscription. Uses GlobalTrialConfig or plan trial_days to begin a trial."""
    now = now or timezone.now()
    from contexts.billing.models import GlobalTrialConfig
    trial_config = GlobalTrialConfig.get_solo()

    with tenant_scope(tenant_id), transaction.atomic():
        if Subscription.objects.filter(
            status__in=SubscriptionStatus.occupied()
        ).exists():
            raise ActiveSubscriptionExists(str(tenant_id))

        plan, amount, currency = _plan_and_price(plan_code, interval)
        
        # Apply Coupon Discount
        coupon_obj = None
        discount_amount = Decimal("0.00")
        if coupon_code:
            try:
                coupon_obj = SubscriptionCoupon.objects.get(code=coupon_code)
                is_valid, _ = coupon_obj.is_valid_now(cart_amount=amount, tenant_status="new")
                if is_valid:
                    if coupon_obj.discount_type == 'percentage':
                        discount = amount * (coupon_obj.value / Decimal("100"))
                        if coupon_obj.maximum_discount_amount and discount > coupon_obj.maximum_discount_amount:
                            discount = coupon_obj.maximum_discount_amount
                        discount_amount = discount
                    else:
                        discount_amount = coupon_obj.value
                    
                    amount = max(Decimal("0.00"), amount - discount_amount)
            except SubscriptionCoupon.DoesNotExist:
                pass

        trial_days = trial_config.trial_days if trial_config.is_enabled else 0
        if plan.trial_days > 0:
            trial_days = plan.trial_days

        if trial_days > 0:
            trial_end = now + timedelta(days=trial_days)
            grace_until = trial_end + timedelta(days=trial_config.grace_days or plan.grace_days)
            return Subscription.objects.create(
                plan=plan, interval=interval,
                price_amount=amount, currency=currency,
                status=SubscriptionStatus.TRIALING,
                trial_end=trial_end,
                current_period_start=now, current_period_end=trial_end,
                grace_until=grace_until,
            )

        period_end = add_interval(now, interval)
        subscription = Subscription.objects.create(
            plan=plan, interval=interval,
            price_amount=amount, currency=currency,
            status=SubscriptionStatus.PAST_DUE,
            current_period_start=now, current_period_end=period_end,
            grace_until=now + timedelta(days=plan.grace_days),
        )
        
        if coupon_obj and discount_amount > 0:
            CouponUsage.objects.create(
                coupon=coupon_obj,
                tenant_id=tenant_id,
                subscription=subscription,
                used_at=now,
                discount_amount=discount_amount
            )

        invoice_service.generate_invoice(
            tenant_id, subscription, now, period_end, now
        )
        return subscription


def change_plan(
    tenant_id: uuid.UUID, new_plan_code: str, interval: str
) -> Subscription:
    """Switch plan/interval. Takes effect from the next renewal (no proration)."""
    with tenant_scope(tenant_id), transaction.atomic():
        sub = entitlements.get_active_subscription(tenant_id)
        if sub is None:
            raise NoActiveSubscription(str(tenant_id))
        plan, price = _plan_and_price(new_plan_code, interval)
        sub.plan = plan
        sub.interval = interval
        sub.price_amount = price.amount
        sub.currency = price.currency
        sub.save(update_fields=[
            "plan", "interval", "price_amount", "currency", "updated_at"
        ])
        return sub


def cancel(
    tenant_id: uuid.UUID, *, at_period_end: bool = True, now: datetime | None = None
) -> Subscription:
    now = now or timezone.now()
    with tenant_scope(tenant_id), transaction.atomic():
        sub = entitlements.get_active_subscription(tenant_id)
        if sub is None:
            raise NoActiveSubscription(str(tenant_id))
        sub.auto_renew = False
        sub.canceled_at = now
        sub.status = (
            SubscriptionStatus.CANCELED
            if at_period_end
            else SubscriptionStatus.EXPIRED
        )
        sub.save(update_fields=[
            "auto_renew", "canceled_at", "status", "updated_at"
        ])
        return sub
