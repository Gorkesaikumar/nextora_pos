"""Purchase Order and receipt lines."""
from django.db import models

from contexts.inventory.domain.enums import PurchaseOrderStatus
from shared.tenancy.models import TenantAwareModel


class PurchaseOrder(TenantAwareModel):
    """
    A purchase order raised to a supplier to replenish stock.
    Transitions: DRAFT → SENT → PARTIALLY_RECEIVED → RECEIVED | CANCELLED.
    """
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    order_number = models.CharField(max_length=50, help_text="Auto-generated PO number, e.g., PO-2024-001")
    status = models.CharField(
        max_length=25,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Financial totals (denormalized for fast display)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Who approved the PO
    approved_by_id = models.UUIDField(
        null=True, blank=True,
        help_text="Cross-context soft FK to identity.User"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "purchase_order"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "order_number"],
                condition=models.Q(is_deleted=False),
                name="uq_purchase_order__tenant_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} — {self.supplier.name}"


class PurchaseOrderLine(TenantAwareModel):
    """A single line on a Purchase Order."""
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="purchase_lines",
    )
    quantity_ordered = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_received = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Running total received across all receipts"
    )
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)
    tax_rate = models.DecimalField(
        max_digits=6, decimal_places=4, default=0,
        help_text="GST / tax rate as a decimal fraction, e.g., 0.18 for 18%"
    )
    # Denormalized totals
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "purchase_order_line"
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "inventory_item"],
                condition=models.Q(is_deleted=False),
                name="uq_po_line__po_item",
            ),
            models.CheckConstraint(
                check=models.Q(quantity_ordered__gt=0),
                name="ck_po_line__qty_gt_zero",
            ),
        ]

    @property
    def quantity_pending(self) -> "Decimal":
        return self.quantity_ordered - self.quantity_received

    def __str__(self) -> str:
        return f"{self.purchase_order.order_number} / {self.inventory_item.product_sku}"
