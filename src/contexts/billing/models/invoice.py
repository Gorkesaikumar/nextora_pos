"""Subscription invoices (platform billing) + gapless numbering sequence.

These are the invoices Nextora issues to its TENANTS for the SaaS subscription —
distinct from the customer sales invoices in the invoicing context.
"""
from django.db import models

from contexts.billing.domain.enums import InvoiceStatus
from shared.infrastructure.models.base import TimeStampedModel, UUIDModel
from shared.tenancy.models import TenantAwareModel


class BillingSequence(UUIDModel, TimeStampedModel):
    """Per-year counter for gapless subscription-invoice numbers.

    Global (not tenant-scoped): platform invoice numbers are unique across all
    tenants. Numbers are issued under a row lock (see invoice_service).
    """

    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "billing_sequence"


class SubscriptionInvoice(TenantAwareModel):
    subscription = models.ForeignKey(
        "billing.Subscription", on_delete=models.PROTECT, related_name="invoices"
    )
    number = models.CharField(max_length=30, unique=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    status = models.CharField(
        max_length=16, choices=InvoiceStatus.choices,
        default=InvoiceStatus.OPEN, db_index=True,
    )
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    provider_order_id = models.CharField(max_length=120, blank=True)  # Razorpay order
    provider_invoice_id = models.CharField(max_length=120, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "subscription_invoice"
        constraints = [
            models.CheckConstraint(
                check=models.Q(total=models.F("amount") + models.F("tax_amount")),
                name="ck_sub_invoice__total_math",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "due_at"],
                name="ix_sub_invoice__unpaid",
                condition=models.Q(status="open"),
            ),
        ]

    def __str__(self) -> str:
        return self.number
