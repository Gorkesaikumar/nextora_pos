"""Modifier groups & modifiers (tenant-scoped, reusable across products)."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class ModifierGroup(TenantAwareModel):
    name = models.CharField(max_length=120)        # "Add-ons", "Spice level"
    min_select = models.PositiveIntegerField(default=0)
    max_select = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "modifier_group"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_modifier_group__tenant_name",
            ),
            models.CheckConstraint(
                check=models.Q(max_select__gte=models.F("min_select")),
                name="ck_modifier_group__min_le_max",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Modifier(TenantAwareModel):
    group = models.ForeignKey(
        ModifierGroup, on_delete=models.CASCADE, related_name="modifiers"
    )
    name = models.CharField(max_length=120)        # "Extra cheese"
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "modifier"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_modifier__group_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProductModifierGroup(TenantAwareModel):
    """Attaches a modifier group to a product with a per-product ordering."""

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="modifier_links"
    )
    group = models.ForeignKey(
        ModifierGroup, on_delete=models.PROTECT, related_name="product_links"
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "product_modifier_group"
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "group"],
                condition=models.Q(is_deleted=False),
                name="uq_product_modifier_group",
            ),
        ]
