"""Data access for the InventoryItem master (stock per product × warehouse)."""
import uuid

from django.db import models

from contexts.inventory.models import InventoryItem

from .base import BaseRepository


class InventoryItemRepository(BaseRepository[InventoryItem]):
    model = InventoryItem

    def get_for_product_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> InventoryItem | None:
        return self.get_queryset().filter(
            product_id=product_id, warehouse_id=warehouse_id
        ).first()

    def lock_for_product_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> InventoryItem | None:
        """Row-locked fetch by natural key (for the ledger write path)."""
        return (
            self.get_queryset()
            .select_for_update()
            .filter(product_id=product_id, warehouse_id=warehouse_id)
            .first()
        )

    def for_warehouse(self, warehouse_id: uuid.UUID) -> models.QuerySet[InventoryItem]:
        return self.get_queryset().filter(warehouse_id=warehouse_id, is_active=True)

    def below_reorder_point(self) -> models.QuerySet[InventoryItem]:
        """Items whose available + on-order has fallen to/under the reorder point.

        Used by the reorder suggestion engine; relies on the partial index over
        ``quantity_on_hand`` for an indexed scan rather than a full table walk.
        """
        return self.get_queryset().filter(
            is_active=True,
            reorder_point__gt=0,
            quantity_on_hand__lte=models.F("reorder_point"),
        )

    def below_minimum(self) -> models.QuerySet[InventoryItem]:
        return self.get_queryset().filter(
            is_active=True,
            minimum_stock__gt=0,
            quantity_on_hand__lte=models.F("minimum_stock"),
        )
