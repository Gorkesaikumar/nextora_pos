"""Data access for inventory alerts."""
import uuid

from django.db import models

from contexts.inventory.domain.enums import AlertStatus, AlertType
from contexts.inventory.models import InventoryAlert

from .base import BaseRepository


class InventoryAlertRepository(BaseRepository[InventoryAlert]):
    model = InventoryAlert

    def open_alerts(self) -> models.QuerySet[InventoryAlert]:
        return self.get_queryset().filter(status=AlertStatus.OPEN)

    def open_for_item(
        self, item_id: uuid.UUID, alert_type: AlertType
    ) -> InventoryAlert | None:
        return self.get_queryset().filter(
            inventory_item_id=item_id,
            alert_type=alert_type,
            status=AlertStatus.OPEN,
        ).first()

    def resolve_open(
        self, item_id: uuid.UUID, alert_types: list[AlertType], *, resolved_at
    ) -> int:
        """Auto-resolve open alerts of the given types once the condition clears."""
        return self.get_queryset().filter(
            inventory_item_id=item_id,
            alert_type__in=alert_types,
            status=AlertStatus.OPEN,
        ).update(status=AlertStatus.RESOLVED, resolved_at=resolved_at)
