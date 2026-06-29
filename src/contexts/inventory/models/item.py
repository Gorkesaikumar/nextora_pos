"""InventoryItem — the master stock-keeping record per product per warehouse."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class InventoryItem(TenantAwareModel):
    """
    Master stock record that tracks quantity on hand for a specific product
    in a specific warehouse. This is the canonical inventory record linked
    from the catalog via product.inventory_item_id.
    """
    # Cross-context soft FK: the product in the catalog context
    product_id = models.UUIDField(
        help_text="Cross-context soft FK to catalog.Product"
    )
    product_sku = models.CharField(
        max_length=64, help_text="Denormalized SKU for fast query and display"
    )
    product_name = models.CharField(
        max_length=200, help_text="Denormalized name for display without JOIN"
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="inventory_items",
    )

    # Quantities (all stored in the product's base unit)
    quantity_on_hand = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Current quantity available in this warehouse"
    )
    quantity_reserved = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Quantity reserved by open orders, not yet dispatched"
    )
    quantity_on_order = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Quantity on open purchase orders, not yet received"
    )

    # Stock controls
    minimum_stock = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Triggers a low-stock alert when quantity_on_hand falls below this"
    )
    reorder_point = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Threshold below which a purchase order should be placed"
    )
    reorder_quantity = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Suggested quantity to order when replenishing"
    )

    # Costing
    average_cost = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        help_text="Weighted-average cost per unit (updated on each purchase receipt)"
    )

    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "inventory_item"
        ordering = ["product_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product_id", "warehouse"],
                condition=models.Q(is_deleted=False),
                name="uq_inventory_item__tenant_product_warehouse",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "warehouse", "quantity_on_hand"],
                name="ix_inv_item__tenant_wh_qty",
            ),
        ]

    @property
    def quantity_available(self) -> "Decimal":
        """Net quantity available for sale (on_hand minus reserved)."""
        return self.quantity_on_hand - self.quantity_reserved

    def __str__(self) -> str:
        return f"{self.product_sku} @ {self.warehouse.code}"
