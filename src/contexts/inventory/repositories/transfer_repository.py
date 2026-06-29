"""Data access for inter-warehouse transfers."""
import uuid

from django.db import models

from contexts.inventory.models import StockTransfer, StockTransferLine

from .base import BaseRepository


class StockTransferRepository(BaseRepository[StockTransfer]):
    model = StockTransfer

    def with_lines(self) -> models.QuerySet[StockTransfer]:
        return self.get_queryset().select_related(
            "from_warehouse", "to_warehouse"
        ).prefetch_related("lines")

    def lock(self, entity_id: uuid.UUID) -> StockTransfer | None:
        return self.get_queryset().select_for_update().filter(pk=entity_id).first()

    def number_exists(self, transfer_number: str) -> bool:
        return self.get_queryset().filter(transfer_number=transfer_number).exists()


class StockTransferLineRepository(BaseRepository[StockTransferLine]):
    model = StockTransferLine

    def for_transfer(self, transfer_id: uuid.UUID) -> models.QuerySet[StockTransferLine]:
        # Ordered by inventory_item id so locks are always taken in a
        # deterministic order (deadlock avoidance — ADR-0001 review R3).
        return (
            self.get_queryset()
            .filter(transfer_id=transfer_id)
            .select_related("inventory_item", "batch")
            .order_by("inventory_item_id")
        )
