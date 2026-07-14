"""Warehouse model — physical storage locations."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class Warehouse(TenantAwareModel):
    """Physical warehouse / storage location (e.g., "Main Store", "Cold Room")."""
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, help_text="Short identifier, e.g., WH-01")
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta(TenantAwareModel.Meta):
        db_table = "warehouse"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_warehouse__tenant_code",
            ),
            # Enforce single default warehouse per tenant.
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_default=True, is_deleted=False),
                name="uq_warehouse__one_default",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
