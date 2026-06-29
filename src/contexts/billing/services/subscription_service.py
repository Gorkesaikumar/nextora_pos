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
from contexts.billing.models import Plan, Subscription
from contexts.billing.services import entitlements, invoice_service
from shared.tenancy import tenant_scope


def _plan_and_price(plan_code: str, interval: str):
    try:
        plan = Plan.objects.get(code=plan_code, is_active=True)
    except Plan.DoesNotExist as exc:
        raise PlanNotFound(plan_code) from exc
    price = plan.prices.filter(interval=interval).first()
    if price is None:
        raise PriceNotFound(f"{plan_code}/{interval}")
    return plan, price


def create_subscription(
    tenant_id: uuid.UUID,
    plan_code: str,
    interval: str,
    now: datetime | None = None,
) -> Subscription:
    """Start a subscription. With trial_days>0 begins a trial; otherwise issues
    an open invoice immediately and starts in a (grace) past_due state until paid.
    """
    now = now or timezone.now()
    with tenant_scope(tenant_id), transaction.atomic():
        if Subscription.objects.filter(
            status__in=SubscriptionStatus.occupied()
        ).exists():
            raise ActiveSubscriptionExists(str(tenant_id))

        plan, price = _plan_and_price(plan_code, interval)

        if plan.trial_days > 0:
            trial_end = now + timedelta(days=plan.trial_days)
            return Subscription.objects.create(
                plan=plan, interval=interval,
                price_amount=price.amount, currency=price.currency,
                status=SubscriptionStatus.TRIALING,
                trial_end=trial_end,
                current_period_start=now, current_period_end=trial_end,
            )

        period_end = add_interval(now, interval)
        subscription = Subscription.objects.create(
            plan=plan, interval=interval,
            price_amount=price.amount, currency=price.currency,
            status=SubscriptionStatus.PAST_DUE,
            current_period_start=now, current_period_end=period_end,
            grace_until=now + timedelta(days=plan.grace_days),
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
