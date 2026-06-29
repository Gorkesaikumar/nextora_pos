"""Data access for stock adjustments and damaged-stock records."""
import uuid

from django.db import models

from contexts.inventory.models import (
    DamagedStock,
    StockAdjustment,
    StockAdjustmentLine,
)

from .base import BaseRepository


class StockAdjustmentRepository(BaseRepository[StockAdjustment]):
    model = StockAdjustment

    def with_lines(self) -> models.QuerySet[StockAdjustment]:
        return self.get_queryset().select_related("warehouse").prefetch_related("lines")

    def lock(self, entity_id: uuid.UUID) -> StockAdjustment | None:
        return self.get_queryset().select_for_update().filter(pk=entity_id).first()

    def number_exists(self, adjustment_number: str) -> bool:
        return self.get_queryset().filter(adjustment_number=adjustment_number).exists()


class StockAdjustmentLineRepository(BaseRepository[StockAdjustmentLine]):
    model = StockAdjustmentLine

    def for_adjustment(self, adjustment_id: uuid.UUID) -> models.QuerySet[StockAdjustmentLine]:
        return (
            self.get_queryset()
            .filter(adjustment_id=adjustment_id)
            .select_related("inventory_item", "batch")
            .order_by("inventory_item_id")
        )


class DamagedStockRepository(BaseRepository[DamagedStock]):
    model = DamagedStock

    def for_item(self, item_id: uuid.UUID) -> models.QuerySet[DamagedStock]:
        return self.get_queryset().filter(inventory_item_id=item_id)
