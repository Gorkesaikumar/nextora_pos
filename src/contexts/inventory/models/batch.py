"""Batch / Lot tracking with expiry dates."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class Batch(TenantAwareModel):
    """
    A batch / lot of stock with an expiry date. A single InventoryItem can have
    multiple batches (e.g., different manufacture dates / expiry windows).
    Batch-tracked items consume FEFO (First Expired, First Out) by default.
    """
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="batches",
    )
    batch_number = models.CharField(max_length=80, help_text="Manufacturer batch / lot number")
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    quantity = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Current quantity remaining in this batch"
    )
    unit_cost = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        help_text="Cost per unit at the time this batch was received"
    )

    # Source purchase order reference
    purchase_order_id = models.UUIDField(
        null=True, blank=True,
        help_text="Soft FK to the PurchaseOrder that created this batch"
    )

    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "inventory_batch"
        ordering = ["expiry_date", "manufacture_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["inventory_item", "batch_number"],
                condition=models.Q(is_deleted=False),
                name="uq_batch__item_number",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="ck_batch__qty_nonneg",
            ),
        ]
        indexes = [
            models.Index(
                fields=["inventory_item", "expiry_date"],
                name="ix_batch__item_expiry",
            ),
        ]

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        if self.expiry_date is None:
            return False
        return self.expiry_date < timezone.now().date()

    def __str__(self) -> str:
        return f"Batch {self.batch_number} ({self.inventory_item.product_sku})"
