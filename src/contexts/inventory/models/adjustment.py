"""Stock adjustments and damaged stock write-offs."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class AdjustmentReason(models.TextChoices):
    PHYSICAL_COUNT = "physical_count", "Physical Count / Stocktake"
    DAMAGED = "damaged", "Damaged / Spoilage"
    THEFT = "theft", "Theft / Shrinkage"
    EXPIRED = "expired", "Expired Goods"
    CORRECTION = "correction", "Data Correction"
    PROMOTIONAL = "promotional", "Promotional Sample"
    OTHER = "other", "Other"


class StockAdjustment(TenantAwareModel):
    """
    A manual stock correction. Can add or remove quantity. Each adjustment
    triggers a corresponding StockMovement for full audit traceability.
    """
    adjustment_number = models.CharField(max_length=50)
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="adjustments",
    )
    reason = models.CharField(max_length=30, choices=AdjustmentReason.choices)
    notes = models.TextField(blank=True)
    adjusted_by_id = models.UUIDField(null=True, blank=True, help_text="Actor who performed adjustment")
    approved_by_id = models.UUIDField(null=True, blank=True, help_text="Supervisor who approved")
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "stock_adjustment"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "adjustment_number"],
                condition=models.Q(is_deleted=False),
                name="uq_adjustment__tenant_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.adjustment_number} ({self.reason})"


class StockAdjustmentLine(TenantAwareModel):
    """A single item line within a stock adjustment."""
    adjustment = models.ForeignKey(
        StockAdjustment, on_delete=models.CASCADE, related_name="lines"
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="adjustment_lines",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="adjustment_lines",
    )
    quantity_before = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_after = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    @property
    def quantity_delta(self) -> "Decimal":
        """Signed change: positive = stock added, negative = stock removed."""
        return self.quantity_after - self.quantity_before

    class Meta(TenantAwareModel.Meta):
        db_table = "stock_adjustment_line"
        constraints = [
            models.UniqueConstraint(
                fields=["adjustment", "inventory_item"],
                condition=models.Q(is_deleted=False),
                name="uq_adj_line__adjustment_item",
            ),
            models.CheckConstraint(
                check=models.Q(quantity_after__gte=0),
                name="ck_adj_line__qty_after_nonneg",
            ),
        ]

    def __str__(self) -> str:
        delta = self.quantity_after - self.quantity_before
        sign = "+" if delta >= 0 else ""
        return f"{self.adjustment.adjustment_number} / {self.inventory_item.product_sku}: {sign}{delta}"


class DamagedStock(TenantAwareModel):
    """
    Explicit record of damaged / spoiled stock separate from generic adjustments.
    Supports insurance claims and compliance reporting.
    """
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="damaged_records",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="damaged_records",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="damaged_records",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    damage_reason = models.CharField(max_length=255)
    incident_date = models.DateField()
    reported_by_id = models.UUIDField(null=True, blank=True)
    # Reference to generated adjustment for traceability
    adjustment = models.ForeignKey(
        StockAdjustment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="damaged_stock_records",
    )
    image = models.ImageField(
        upload_to="inventory/damage/",
        null=True, blank=True,
        help_text="Optional photo evidence of the damage"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "damaged_stock"
        ordering = ["-incident_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="ck_damaged__qty_gt_zero",
            ),
        ]

    @property
    def total_loss_value(self) -> "Decimal":
        return self.quantity * self.unit_cost

    def __str__(self) -> str:
        return f"Damage: {self.quantity} x {self.inventory_item.product_sku} on {self.incident_date}"
