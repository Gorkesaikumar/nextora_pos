"""Subscription invoice generation and payment settlement."""
import uuid
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from contexts.billing.domain.enums import (
    InvoiceStatus,
    PaymentStatus,
    SubscriptionStatus,
)
from contexts.billing.models import (
    BillingSequence,
    Subscription,
    SubscriptionInvoice,
    SubscriptionPayment,
)
from shared.tenancy import tenant_scope


def _next_invoice_number(now: datetime) -> str:
    """Gapless platform invoice number, issued under a row lock."""
    with transaction.atomic():
        seq, _ = BillingSequence.objects.get_or_create(year=now.year)
        seq = BillingSequence.objects.select_for_update().get(pk=seq.pk)
        seq.last_number += 1
        seq.save(update_fields=["last_number", "updated_at"])
        return f"NX-{now.year}-{seq.last_number:06d}"


def generate_invoice(
    tenant_id: uuid.UUID,
    subscription: Subscription,
    period_start: datetime,
    period_end: datetime,
    now: datetime | None = None,
) -> SubscriptionInvoice:
    now = now or timezone.now()
    with tenant_scope(tenant_id), transaction.atomic():
        amount = subscription.price_amount
        return SubscriptionInvoice.objects.create(
            subscription=subscription,
            number=_next_invoice_number(now),
            period_start=period_start,
            period_end=period_end,
            amount=amount,
            tax_amount=0,
            total=amount,
            currency=subscription.currency,
            status=InvoiceStatus.OPEN,
            due_at=period_end,
        )


def mark_paid(
    tenant_id: uuid.UUID,
    invoice: SubscriptionInvoice,
    *,
    provider: str = "",
    provider_payment_id: str = "",
    amount=None,
    now: datetime | None = None,
) -> SubscriptionInvoice:
    """Record a captured payment and roll the subscription forward.

    Idempotent: a second call for an already-paid invoice is a no-op.
    """
    now = now or timezone.now()
    with tenant_scope(tenant_id), transaction.atomic():
        invoice.refresh_from_db()
        if invoice.status == InvoiceStatus.PAID:
            return invoice

        SubscriptionPayment.objects.create(
            invoice=invoice,
            amount=amount if amount is not None else invoice.total,
            currency=invoice.currency,
            status=PaymentStatus.CAPTURED,
            provider=provider,
            provider_payment_id=provider_payment_id,
            captured_at=now,
        )
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = now
        invoice.save(update_fields=["status", "paid_at", "updated_at"])

        _activate_subscription(invoice.subscription, invoice)
        return invoice


def _activate_subscription(
    subscription: Subscription, invoice: SubscriptionInvoice
) -> None:
    subscription.current_period_start = invoice.period_start
    subscription.current_period_end = invoice.period_end
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.grace_until = None
    subscription.save(
        update_fields=[
            "current_period_start", "current_period_end",
            "status", "grace_until", "updated_at",
        ]
    )
