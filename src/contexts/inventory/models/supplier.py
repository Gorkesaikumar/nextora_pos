"""Supplier model — vendors from whom stock is purchased."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class Supplier(TenantAwareModel):
    """Vendor / Supplier profile."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, help_text="Short supplier code")
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Tax / GST
    gstin = models.CharField(
        max_length=15, blank=True, help_text="Supplier GSTIN for input tax credit"
    )
    pan = models.CharField(max_length=10, blank=True, help_text="PAN card number")

    # Banking details for payment reconciliation
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_no = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=12, blank=True)

    # Credit terms
    credit_days = models.PositiveIntegerField(
        default=0, help_text="Payment due within N days of invoice"
    )

    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "supplier"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(is_deleted=False) & ~models.Q(code=""),
                name="uq_supplier__tenant_code",
            ),
        ]

    def __str__(self) -> str:
        return self.name
