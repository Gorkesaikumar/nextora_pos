"""Pricing and Overrides for the Product Catalog."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class PriceTier(TenantAwareModel):
    """
    A logical grouping for branches that share the same pricing structure.
    Solves the O(N) override problem (SARB finding).
    e.g., "Tier 1 - Metro", "Tier 2 - Rural", "Tier 3 - Airport".
    Branches are assigned to a PriceTier in the restaurant domain.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "catalog_price_tier"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_price_tier__tenant_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name
