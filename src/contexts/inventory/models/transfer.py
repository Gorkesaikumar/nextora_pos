"""Inter-warehouse transfer models."""
from django.db import models

from contexts.inventory.domain.enums import TransferStatus
from shared.tenancy.models import TenantAwareModel


class StockTransfer(TenantAwareModel):
    """
    A request to move stock from one warehouse to another.
    Transitions: DRAFT → IN_TRANSIT → RECEIVED | CANCELLED.
    When status moves to RECEIVED, stock movements are created automatically.
    """
    transfer_number = models.CharField(max_length=50, help_text="Auto-generated transfer number")
    from_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    to_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    status = models.CharField(
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.DRAFT,
    )
    expected_date = models.DateField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    dispatched_by_id = models.UUIDField(null=True, blank=True)
    received_by_id = models.UUIDField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "stock_transfer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "transfer_number"],
                condition=models.Q(is_deleted=False),
                name="uq_transfer__tenant_number",
            ),
            models.CheckConstraint(
                check=~models.Q(from_warehouse=models.F("to_warehouse")),
                name="ck_transfer__different_warehouses",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transfer_number}: {self.from_warehouse.code} → {self.to_warehouse.code}"


class StockTransferLine(TenantAwareModel):
    """A single line within a stock transfer."""
    transfer = models.ForeignKey(
        StockTransfer, on_delete=models.CASCADE, related_name="lines"
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="transfer_lines",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="transfer_lines",
        help_text="Specific batch being transferred, if batch-tracked"
    )
    quantity_requested = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_dispatched = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "stock_transfer_line"
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "inventory_item"],
                condition=models.Q(is_deleted=False),
                name="uq_transfer_line__transfer_item",
            ),
            models.CheckConstraint(
                check=models.Q(quantity_requested__gt=0),
                name="ck_transfer_line__qty_gt_zero",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transfer.transfer_number} / {self.inventory_item.product_sku}"
