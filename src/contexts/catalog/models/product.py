"""Product, variants and images (tenant-scoped)."""
from django.db import models

from contexts.catalog.domain.enums import ProductType
from shared.tenancy.models import TenantAwareModel


class Product(TenantAwareModel):
    category = models.ForeignKey(
        "catalog.Category", on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type = models.CharField(
        max_length=12, choices=ProductType.choices, default=ProductType.FOOD
    )

    # Identity codes.
    sku = models.CharField(max_length=64)
    barcode = models.CharField(max_length=64, null=True, blank=True)

    # GST / HSN.
    hsn_code = models.CharField(max_length=8, blank=True)
    tax_class = models.ForeignKey(
        "catalog.TaxClass", on_delete=models.PROTECT,
        null=True, blank=True, related_name="products",
    )
    
    # Unit of Measure
    unit = models.ForeignKey(
        "catalog.Unit", on_delete=models.PROTECT,
        null=True, blank=True, related_name="products",
    )

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    # Routing overrides (fall back to category defaults).
    kitchen_station = models.ForeignKey(
        "catalog.KitchenStation", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="products",
    )
    printer = models.ForeignKey(
        "catalog.Printer", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="products",
    )

    image = models.ImageField(upload_to="catalog/products/", null=True, blank=True)
    
    # Inventory
    track_inventory = models.BooleanField(default=True)
    inventory_item_id = models.UUIDField(null=True, blank=True, help_text="Cross-context reference to Inventory Item")
    
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    modifier_groups = models.ManyToManyField(
        "catalog.ModifierGroup",
        through="catalog.ProductModifierGroup",
        related_name="products",
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "product"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                condition=models.Q(is_deleted=False),
                name="uq_product__tenant_sku",
            ),
            models.UniqueConstraint(
                fields=["tenant", "barcode"],
                condition=models.Q(is_deleted=False) & ~models.Q(barcode=None),
                name="uq_product__tenant_barcode",
            ),
            models.CheckConstraint(
                check=models.Q(base_price__gte=0), name="ck_product__price_nonneg"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "category"],
                name="ix_product__tenant_category",
                condition=models.Q(is_active=True, is_deleted=False),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"


class ProductVariant(TenantAwareModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    name = models.CharField(max_length=120)        # "Large", "500ml"
    sku = models.CharField(max_length=64)
    barcode = models.CharField(max_length=64, null=True, blank=True)
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "product_variant"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                condition=models.Q(is_deleted=False),
                name="uq_variant__tenant_sku",
            ),
            models.UniqueConstraint(
                fields=["product", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_variant__product_name",
            ),
            # Exactly one default variant per product.
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_default=True, is_deleted=False),
                name="uq_variant__one_default",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}:{self.name}"


class ProductImage(TenantAwareModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="catalog/products/gallery/")
    alt_text = models.CharField(max_length=160, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "product_image"
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True, is_deleted=False),
                name="uq_product_image__one_primary",
            ),
        ]


class ProductComboItem(TenantAwareModel):
    """Links a combo product to its component products."""
    combo = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="combo_items",
        limit_choices_to={'type': ProductType.COMBO}
    )
    component = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="part_of_combos"
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    price_override = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Fixed price for this item within the combo, if applicable."
    )
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "product_combo_item"
        constraints = [
            models.UniqueConstraint(
                fields=["combo", "component"],
                condition=models.Q(is_deleted=False),
                name="uq_combo_item__combo_component",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.combo.name} -> {self.quantity}x {self.component.name}"
