"""Tax invoice — one per settled order, daily-reset number."""
from django.db import models
from django.utils import timezone

from contexts.ordering.domain.enums import InvoiceStatus
from shared.tenancy.models import TenantAwareModel

_MONEY = {"max_digits": 12, "decimal_places": 2, "default": 0}


class Invoice(TenantAwareModel):
    order = models.OneToOneField(
        "ordering.Order", on_delete=models.PROTECT, related_name="invoice"
    )
    number = models.CharField(max_length=40)
    series = models.CharField(max_length=20, default="INV")
    financial_year = models.CharField(max_length=9)
    status = models.CharField(
        max_length=8, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED
    )

    # Frozen totals (independent of later order edits).
    subtotal = models.DecimalField(**_MONEY)
    discount_amount = models.DecimalField(**_MONEY)
    service_charge_amount = models.DecimalField(**_MONEY)
    taxable_amount = models.DecimalField(**_MONEY)
    cgst = models.DecimalField(**_MONEY)
    sgst = models.DecimalField(**_MONEY)
    igst = models.DecimalField(**_MONEY)
    cess = models.DecimalField(**_MONEY)
    tax_amount = models.DecimalField(**_MONEY)
    round_off = models.DecimalField(**_MONEY)
    total = models.DecimalField(**_MONEY)

    customer_name = models.CharField(max_length=160, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    issued_at = models.DateTimeField(default=timezone.now)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=255, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "tax_invoice"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"], name="uq_invoice__tenant_number"
            ),
        ]

    def __str__(self) -> str:
        return self.number
