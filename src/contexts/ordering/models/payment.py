"""Payments and refunds against an order (partial + multiple methods)."""
from django.db import models
from django.utils import timezone

from contexts.ordering.domain.enums import (
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from shared.tenancy.models import TenantAwareModel

_MONEY = {"max_digits": 12, "decimal_places": 2, "default": 0}


class Payment(TenantAwareModel):
    order = models.ForeignKey(
        "ordering.Order", on_delete=models.PROTECT, related_name="payments"
    )
    kind = models.CharField(
        max_length=8, choices=PaymentKind.choices, default=PaymentKind.PAYMENT
    )
    method = models.CharField(max_length=8, choices=PaymentMethod.choices)
    amount = models.DecimalField(**_MONEY)
    tendered = models.DecimalField(null=True, blank=True, max_digits=12, decimal_places=2)
    change_due = models.DecimalField(**_MONEY)
    reference = models.CharField(max_length=120, blank=True)   # UPI/card txn ref
    status = models.CharField(
        max_length=8, choices=PaymentStatus.choices, default=PaymentStatus.CAPTURED
    )
    idempotency_key = models.CharField(max_length=120, blank=True)
    refund_reason = models.CharField(max_length=255, blank=True)
    captured_at = models.DateTimeField(default=timezone.now)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "order_payment"
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="ck_payment__amount_pos"
            ),
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_payment__idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["order"], name="ix_payment__order"),
            models.Index(
                fields=["tenant", "captured_at"],
                name="ix_payment__tenant_captured",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.method}:{self.amount}"
