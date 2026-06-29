"""End-to-end billing tests: lifecycle, limits, usage, webhooks."""
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from contexts.billing.domain import metrics
from contexts.billing.domain.periods import add_interval
from contexts.billing.exceptions import (
    ActiveSubscriptionExists,
    GatewayError,
    LimitExceeded,
)
from contexts.billing.gateways import get_gateway, reset_gateway_cache
from contexts.billing.models import (
    Plan,
    PlanPrice,
    Subscription,
    SubscriptionInvoice,
)
from contexts.billing.services import (
    invoice_service,
    lifecycle,
    subscription_service,
    usage,
    webhook_service,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def make_plan(db):
    def _make(
        code="pro",
        *,
        trial_days=14,
        grace_days=7,
        monthly=Decimal("999.00"),
        max_branches=None,
        max_employees=None,
        max_invoices_per_month=None,
        max_storage_mb=None,
        features=None,
    ) -> Plan:
        plan = Plan.objects.create(
            code=code, name=code.title(),
            trial_days=trial_days, grace_days=grace_days,
            max_branches=max_branches, max_employees=max_employees,
            max_invoices_per_month=max_invoices_per_month,
            max_storage_mb=max_storage_mb,
            features=features or {},
        )
        for interval, mult in (("monthly", 1), ("quarterly", 3), ("yearly", 11)):
            PlanPrice.objects.create(
                plan=plan, interval=interval,
                amount=monthly * mult, currency="INR",
            )
        return plan

    return _make


def _sub(tenant):
    return Subscription.all_objects.get(tenant_id=tenant.id)


# --- Creation --------------------------------------------------------------
def test_create_trial_subscription(tenant, make_plan):
    make_plan(trial_days=14)
    sub = subscription_service.create_subscription(tenant.id, "pro", "monthly")

    assert sub.status == "trialing"
    assert sub.trial_end is not None
    assert sub.has_access()


def test_create_without_trial_issues_open_invoice(tenant, make_plan):
    make_plan(trial_days=0)
    sub = subscription_service.create_subscription(tenant.id, "pro", "monthly")

    assert sub.status == "past_due"
    invoice = SubscriptionInvoice.all_objects.get(tenant_id=tenant.id)
    assert invoice.status == "open"
    assert invoice.total == Decimal("999.00")
    assert sub.has_access()  # within grace


def test_one_live_subscription_per_tenant(tenant, make_plan):
    make_plan()
    subscription_service.create_subscription(tenant.id, "pro", "monthly")
    with pytest.raises(ActiveSubscriptionExists):
        subscription_service.create_subscription(tenant.id, "pro", "monthly")


# --- Renewal / period math -------------------------------------------------
def test_trial_to_active_renewal_extends_period(tenant, make_plan):
    now = timezone.now()
    make_plan(trial_days=14)
    sub = subscription_service.create_subscription(
        tenant.id, "pro", "monthly", now=now
    )
    trial_end = sub.trial_end

    # Trial ends -> first invoice issued, status past_due.
    lifecycle.run_billing_cycle(now=trial_end)
    sub = _sub(tenant)
    assert sub.status == "past_due"

    invoice = (
        SubscriptionInvoice.all_objects.filter(tenant_id=tenant.id)
        .latest("created_at")
    )
    invoice_service.mark_paid(tenant.id, invoice, now=trial_end)

    sub = _sub(tenant)
    assert sub.status == "active"
    assert sub.current_period_end == add_interval(trial_end, "monthly")


def test_grace_period_then_expiry(tenant, make_plan):
    now = timezone.now()
    make_plan(trial_days=0, grace_days=7)
    sub = subscription_service.create_subscription(
        tenant.id, "pro", "monthly", now=now
    )
    assert sub.status == "past_due"

    # Past the grace window, unpaid -> expired.
    future = now + timedelta(days=8)
    lifecycle.run_billing_cycle(now=future)

    sub = _sub(tenant)
    assert sub.status == "expired"
    assert not sub.has_access(now=future)


# --- Limits / entitlements -------------------------------------------------
def test_employee_limit_enforced(tenant, make_plan, make_user, system_role):
    make_plan(max_employees=2)
    subscription_service.create_subscription(tenant.id, "pro", "monthly")

    from contexts.identity.models import Membership

    role = system_role("cashier")
    Membership.objects.create(user=make_user(), tenant=tenant, role=role)
    Membership.objects.create(user=make_user(), tenant=tenant, role=role)

    assert usage.current_usage(tenant.id, metrics.EMPLOYEES) == 2
    assert not usage.check_limit(tenant.id, metrics.EMPLOYEES)
    with pytest.raises(LimitExceeded):
        usage.enforce_limit(tenant.id, metrics.EMPLOYEES)


def test_null_limit_is_unlimited(tenant, make_plan):
    make_plan(max_storage_mb=None)
    subscription_service.create_subscription(tenant.id, "pro", "monthly")
    # Must not raise even for a huge request.
    usage.enforce_limit(tenant.id, metrics.STORAGE_MB, by=10_000_000)


def test_periodic_invoice_limit(tenant, make_plan):
    make_plan(max_invoices_per_month=2)
    subscription_service.create_subscription(tenant.id, "pro", "monthly")
    key = usage.month_key_now()

    usage.increment(tenant.id, metrics.INVOICES, by=1, period_key=key)
    usage.increment(tenant.id, metrics.INVOICES, by=1, period_key=key)

    assert usage.current_usage(tenant.id, metrics.INVOICES, key) == 2
    with pytest.raises(LimitExceeded):
        usage.enforce_limit(tenant.id, metrics.INVOICES, period_key=key)


def test_no_subscription_means_zero_allowance(tenant, make_plan):
    # No subscription created -> limit resolves to 0 -> any usage denied.
    with pytest.raises(LimitExceeded):
        usage.enforce_limit(tenant.id, metrics.STORAGE_MB, by=1)


# --- Change plan / cancel --------------------------------------------------
def test_change_plan(tenant, make_plan):
    make_plan(code="pro", monthly=Decimal("999.00"))
    make_plan(code="enterprise", monthly=Decimal("4999.00"))
    subscription_service.create_subscription(tenant.id, "pro", "monthly")

    subscription_service.change_plan(tenant.id, "enterprise", "yearly")
    sub = _sub(tenant)
    assert sub.plan.code == "enterprise"
    assert sub.interval == "yearly"
    assert sub.price_amount == Decimal("4999.00") * 11


def test_cancel_keeps_access_until_period_end(tenant, make_plan):
    make_plan(trial_days=14)
    subscription_service.create_subscription(tenant.id, "pro", "monthly")
    subscription_service.cancel(tenant.id, at_period_end=True)

    sub = _sub(tenant)
    assert sub.status == "canceled"
    assert sub.auto_renew is False
    assert sub.has_access()  # trial period still in the future


# --- Webhooks --------------------------------------------------------------
def test_webhook_marks_invoice_paid_and_is_idempotent(tenant, make_plan, settings):
    settings.BILLING_GATEWAY = "fake"
    reset_gateway_cache()

    make_plan(trial_days=0)
    sub = subscription_service.create_subscription(tenant.id, "pro", "monthly")
    invoice = SubscriptionInvoice.all_objects.get(tenant_id=tenant.id)

    order_id = "order_test_123"
    SubscriptionInvoice.all_objects.filter(id=invoice.id).update(
        provider_order_id=order_id
    )

    gateway = get_gateway()
    body = json.dumps(
        {
            "id": "evt_1",
            "event": "payment.captured",
            "order_id": order_id,
            "payment_id": "pay_1",
            "status": "captured",
        }
    ).encode()
    signature = gateway.sign(body)

    assert webhook_service.handle_webhook(body, signature) == "processed"

    invoice = SubscriptionInvoice.all_objects.get(id=invoice.id)
    assert invoice.status == "paid"
    assert _sub(tenant).status == "active"

    # Redelivery is a no-op.
    assert webhook_service.handle_webhook(body, signature) == "duplicate"


def test_webhook_rejects_bad_signature(tenant, make_plan, settings):
    settings.BILLING_GATEWAY = "fake"
    reset_gateway_cache()
    body = json.dumps({"id": "evt_x", "event": "payment.captured"}).encode()
    with pytest.raises(GatewayError):
        webhook_service.handle_webhook(body, "not-a-valid-signature")
