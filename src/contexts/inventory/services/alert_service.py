"""Alert service — batch expiry scanning and alert lifecycle management."""
import uuid
from datetime import timedelta
from typing import Optional

from django.db.models import F as models_F
from django.db import transaction
from django.utils import timezone


from contexts.inventory.domain.enums import AlertStatus, AlertType
from contexts.inventory.models import Batch, InventoryAlert, InventoryItem


def scan_expiring_batches(days_ahead: int = 30) -> int:
    """
    Scan all batches expiring within `days_ahead` days and raise EXPIRY_SOON alerts.
    Marks already-expired batches with EXPIRED alerts.

    Returns the number of new alerts created.
    """
    today = timezone.now().date()
    expiry_window = today + timedelta(days=days_ahead)
    created_count = 0

    # Batches that are expiring soon (but not yet expired).
    expiring_soon = Batch.objects.filter(
        is_active=True,
        quantity__gt=0,
        expiry_date__gt=today,
        expiry_date__lte=expiry_window,
    ).select_related("inventory_item")

    for batch in expiring_soon:
        _, created = InventoryAlert.objects.get_or_create(
            inventory_item=batch.inventory_item,
            alert_type=AlertType.EXPIRY_SOON,
            status=AlertStatus.OPEN,
            defaults={
                "tenant": batch.inventory_item.tenant,
                "batch": batch,
                "message": (
                    f"{batch.inventory_item.product_name} batch {batch.batch_number} "
                    f"expires on {batch.expiry_date} ({(batch.expiry_date - today).days} days remaining). "
                    f"Quantity: {batch.quantity}"
                ),
                "expiry_date": batch.expiry_date,
                "quantity_at_alert": batch.quantity,
                "threshold_value": days_ahead,
            },
        )
        if created:
            created_count += 1

    # Batches that have already expired.
    expired = Batch.objects.filter(
        is_active=True,
        quantity__gt=0,
        expiry_date__lte=today,
    ).select_related("inventory_item")

    for batch in expired:
        _, created = InventoryAlert.objects.get_or_create(
            inventory_item=batch.inventory_item,
            alert_type=AlertType.EXPIRED,
            status=AlertStatus.OPEN,
            defaults={
                "tenant": batch.inventory_item.tenant,
                "batch": batch,
                "message": (
                    f"{batch.inventory_item.product_name} batch {batch.batch_number} "
                    f"EXPIRED on {batch.expiry_date}. "
                    f"Remaining quantity: {batch.quantity} — Please write off or quarantine."
                ),
                "expiry_date": batch.expiry_date,
                "quantity_at_alert": batch.quantity,
            },
        )
        if created:
            created_count += 1

    return created_count


def scan_low_stock_items() -> int:
    """
    Scan all inventory items for low stock / out of stock conditions.
    Creates alerts for items where quantity_on_hand <= minimum_stock.

    Returns the number of new alerts created.
    """
    created_count = 0

    # Out of stock
    oos_items = InventoryItem.objects.filter(
        is_active=True,
        minimum_stock__gt=0,
        quantity_on_hand__lte=0,
    )
    for item in oos_items:
        _, created = InventoryAlert.objects.get_or_create(
            inventory_item=item,
            alert_type=AlertType.OUT_OF_STOCK,
            status=AlertStatus.OPEN,
            defaults={
                "tenant": item.tenant,
                "message": f"{item.product_name} is OUT OF STOCK in {item.warehouse.name}.",
                "quantity_at_alert": item.quantity_on_hand,
                "threshold_value": item.minimum_stock,
            },
        )
        if created:
            created_count += 1

    # Low stock (above zero but below minimum)
    low_items = InventoryItem.objects.filter(
        is_active=True,
        minimum_stock__gt=0,
        quantity_on_hand__gt=0,
        quantity_on_hand__lte=models_F("minimum_stock"),
    )
    for item in low_items:
        _, created = InventoryAlert.objects.get_or_create(
            inventory_item=item,
            alert_type=AlertType.LOW_STOCK,
            status=AlertStatus.OPEN,
            defaults={
                "tenant": item.tenant,
                "message": (
                    f"{item.product_name} is BELOW MINIMUM STOCK in {item.warehouse.name}. "
                    f"On hand: {item.quantity_on_hand} / Minimum: {item.minimum_stock}"
                ),
                "quantity_at_alert": item.quantity_on_hand,
                "threshold_value": item.minimum_stock,
            },
        )
        if created:
            created_count += 1

    return created_count


@transaction.atomic
def acknowledge_alert(
    alert_id: uuid.UUID,
    acknowledged_by_id: Optional[uuid.UUID] = None,
) -> InventoryAlert:
    """Mark an alert as acknowledged."""
    alert = InventoryAlert.objects.select_for_update().get(id=alert_id)
    if alert.status != AlertStatus.OPEN:
        raise ValueError(f"Alert is already {alert.status}.")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by_id = acknowledged_by_id
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["status", "acknowledged_by_id", "acknowledged_at", "updated_at"])
    return alert


@transaction.atomic
def resolve_alert(alert_id: uuid.UUID) -> InventoryAlert:
    """Mark an alert as resolved."""
    alert = InventoryAlert.objects.select_for_update().get(id=alert_id)
    if alert.status == AlertStatus.RESOLVED:
        return alert
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_at", "updated_at"])
    return alert
