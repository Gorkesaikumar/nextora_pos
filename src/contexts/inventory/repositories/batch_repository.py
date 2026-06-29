"""Data access for batches / lots, with FEFO ordering."""
import uuid

from django.db import models

from contexts.inventory.models import Batch

from .base import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    model = Batch

    def fefo_batches(self, item_id: uuid.UUID) -> models.QuerySet[Batch]:
        """Active, in-stock batches in First-Expired-First-Out order.

        Batches with no expiry sort last. The ``(expiry_date, id)`` ordering is
        also the deterministic **lock order** for multi-batch consumption, which
        prevents deadlocks between concurrent deductions.
        """
        return (
            self.get_queryset()
            .filter(inventory_item_id=item_id, is_active=True, quantity__gt=0)
            .order_by(models.F("expiry_date").asc(nulls_last=True), "id")
        )

    def lock_fefo_batches(self, item_id: uuid.UUID) -> models.QuerySet[Batch]:
        return self.fefo_batches(item_id).select_for_update()

    def for_item(self, item_id: uuid.UUID) -> models.QuerySet[Batch]:
        return self.get_queryset().filter(inventory_item_id=item_id)

    def expiring_before(self, cutoff_date) -> models.QuerySet[Batch]:
        """In-stock batches expiring on/before ``cutoff_date`` (for expiry alerts)."""
        return self.get_queryset().filter(
            is_active=True,
            quantity__gt=0,
            expiry_date__isnull=False,
            expiry_date__lte=cutoff_date,
        )
