"""Unit of Measure (UOM) definitions."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class Unit(TenantAwareModel):
    name = models.CharField(max_length=64)       # e.g., "Kilogram", "Piece"
    abbreviation = models.CharField(max_length=16) # e.g., "kg", "pcs"
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "catalog_unit"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "abbreviation"],
                condition=models.Q(is_deleted=False),
                name="uq_unit__tenant_abbreviation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.abbreviation})"
