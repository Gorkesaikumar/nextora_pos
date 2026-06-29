"""Subscription payments (tenant-scoped)."""
from django.db import models

from contexts.billing.domain.enums import PaymentStatus
from shared.tenancy.models import TenantAwareModel


class SubscriptionPayment(TenantAwareModel):
    invoice = models.ForeignKey(
        "billing.SubscriptionInvoice", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(
        max_length=16, choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING, db_index=True,
    )

    provider = models.CharField(max_length=30, blank=True)
    provider_payment_id = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "subscription_payment"
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="ck_sub_payment__amount_pos"
            ),
            # Prevent double-capture on retried gateway callbacks.
            models.UniqueConstraint(
                fields=["provider", "provider_payment_id"],
                condition=~models.Q(provider_payment_id=""),
                name="uq_sub_payment__provider_ref",
            ),
        ]
        indexes = [
            models.Index(fields=["invoice"], name="ix_sub_payment__invoice"),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_id}:{self.amount}:{self.status}"
