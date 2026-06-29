"""Data access for the immutable StockMovement ledger.

The ledger is append-only: this repository never updates or deletes a movement.
It exposes the idempotency lookup and the balance-sum used by reconciliation.
"""
import uuid
from decimal import Decimal

from django.db import models

from contexts.inventory.models import StockMovement

from .base import BaseRepository


class StockMovementRepository(BaseRepository[StockMovement]):
    model = StockMovement

    def for_item(self, item_id: uuid.UUID) -> models.QuerySet[StockMovement]:
        return self.get_queryset().filter(inventory_item_id=item_id)

    def by_key(self, idempotency_key: str) -> StockMovement | None:
        if not idempotency_key:
            return None
        return self.get_queryset().filter(idempotency_key=idempotency_key).first()

    def for_reference(
        self, reference_type: str, reference_id: uuid.UUID
    ) -> models.QuerySet[StockMovement]:
        return self.get_queryset().filter(
            reference_type=reference_type, reference_id=reference_id
        )

    def reference_applied(
        self,
        *,
        reference_type: str,
        reference_id: uuid.UUID,
        movement_type: str,
    ) -> bool:
        """Has this (document, movement_type) already produced a movement?

        Backs at-least-once idempotency: a redelivered event or retried task
        must not double-apply stock.
        """
        if not reference_type or reference_id is None:
            return False
        return self.get_queryset().filter(
            reference_type=reference_type,
            reference_id=reference_id,
            movement_type=movement_type,
        ).exists()

    def key_applied(self, idempotency_key: str) -> bool:
        """Has a movement already been recorded under this idempotency key?

        Backs the service-level exactly-once guard; the DB partial-unique
        ``uq_movement__idempotency`` is the race-proof backstop.
        """
        if not idempotency_key:
            return False
        return self.get_queryset().filter(idempotency_key=idempotency_key).exists()

    def balance_sum(self, item_id: uuid.UUID) -> Decimal:
        """Σ of signed quantities for an item — the ledger's authoritative balance.

        Reconciliation asserts this equals ``InventoryItem.quantity_on_hand``.
        """
        agg = self.get_queryset().filter(inventory_item_id=item_id).aggregate(
            total=models.Sum("quantity")
        )
        return agg["total"] or Decimal("0")
