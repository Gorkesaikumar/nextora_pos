"""Modifier groups & modifiers (tenant-scoped, reusable across products)."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class SelectionType(models.TextChoices):
    SINGLE = "single", "Single Choice (Radio / 1 max)"
    MULTIPLE = "multiple", "Multiple Choice (Checkboxes / Multi)"


class DisplayStyle(models.TextChoices):
    BUTTONS = "buttons", "Buttons / Chips"
    CHECKBOXES = "checkboxes", "Checkboxes / Radio list"
    DROPDOWN = "dropdown", "Dropdown Select"


class PriceType(models.TextChoices):
    FIXED = "fixed", "Fixed Amount (₹)"
    PERCENTAGE = "percentage", "Percentage of Base (%)"
    FREE = "free", "Free / No Charge"


class ModifierGroup(TenantAwareModel):
    name = models.CharField(max_length=120)        # "Add-ons", "Spice level"
    internal_code = models.CharField(max_length=64, blank=True, default="")
    display_name = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    selection_type = models.CharField(
        max_length=20,
        choices=SelectionType.choices,
        default=SelectionType.MULTIPLE,
    )
    min_select = models.PositiveIntegerField(default=0)
    max_select = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    # Display & Printing Flags (Enterprise Phase 2)
    display_style = models.CharField(
        max_length=20,
        choices=DisplayStyle.choices,
        default=DisplayStyle.BUTTONS,
    )
    expand_by_default = models.BooleanField(default=True)
    print_on_invoice = models.BooleanField(default=True)
    print_on_restaurant_copy = models.BooleanField(default=True)
    print_on_kitchen_ticket = models.BooleanField(default=True)

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
                condition=models.Q(max_select__gte=models.F("min_select")),
                name="ck_modifier_group__min_le_max",
            ),
        ]

    def __str__(self) -> str:
        return self.display_name or self.name


class Modifier(TenantAwareModel):
    group = models.ForeignKey(
        ModifierGroup, on_delete=models.CASCADE, related_name="modifiers"
    )
    name = models.CharField(max_length=120)        # "Extra cheese"
    description = models.TextField(blank=True, default="")
    sku = models.CharField(max_length=64, blank=True, default="")
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_type = models.CharField(
        max_length=20,
        choices=PriceType.choices,
        default=PriceType.FIXED,
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="linked_modifiers",
    )
    quantity_consumed = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    color_code = models.CharField(max_length=20, blank=True, default="")
    is_taxable = models.BooleanField(default=True)

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
    """Attaches a modifier group to a product with a per-product ordering and enterprise override rules."""

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="modifier_links"
    )
    group = models.ForeignKey(
        ModifierGroup, on_delete=models.PROTECT, related_name="product_links"
    )
    sort_order = models.PositiveIntegerField(default=0)
    required_override = models.BooleanField(null=True, blank=True, default=None)
    min_select_override = models.PositiveIntegerField(null=True, blank=True, default=None)
    max_select_override = models.PositiveIntegerField(null=True, blank=True, default=None)

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

