"""Inventory alerts — low stock, out of stock, expiry warnings."""
from django.db import models

from contexts.inventory.domain.enums import AlertStatus, AlertType
from shared.tenancy.models import TenantAwareModel


class InventoryAlert(TenantAwareModel):
    """
    System-generated alert for inventory conditions requiring attention.
    Alerts are created automatically by background tasks and resolved
    either automatically or by human acknowledgement.
    """
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="alerts",
        help_text="Populated for expiry-related alerts"
    )
    alert_type = models.CharField(max_length=25, choices=AlertType.choices)
    status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN
    )
    message = models.TextField(help_text="Human-readable alert message")

    # Contextual snapshot at the time the alert was fired
    quantity_at_alert = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    threshold_value = models.DecimalField(
        max_digits=14, decimal_places=3, null=True, blank=True,
        help_text="The minimum_stock / expiry days threshold that was breached"
    )
    expiry_date = models.DateField(
        null=True, blank=True,
        help_text="The expiry date that triggered the alert"
    )

    acknowledged_by_id = models.UUIDField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "inventory_alert"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status", "alert_type"],
                name="ix_alert__tenant_status_type",
            ),
            models.Index(
                fields=["inventory_item", "alert_type", "status"],
                name="ix_alert__item_type_status",
            ),
        ]
        # Prevent duplicate open alerts for the same condition.
        constraints = [
            models.UniqueConstraint(
                fields=["inventory_item", "alert_type"],
                condition=models.Q(status=AlertStatus.OPEN),
                name="uq_alert__item_type_open",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.alert_type}] {self.inventory_item.product_sku} — {self.status}"
