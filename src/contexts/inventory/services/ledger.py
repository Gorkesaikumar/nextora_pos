"""Higher-level ledger operations built on ``apply_stock_movement``.

``consume_stock`` is the FEFO deduction orchestrator the design calls for
(ADR-0001 review A3): it splits an outflow across batches in First-Expired-
First-Out order, posting one movement per batch — keeping all batch selection
inside the single mutation path rather than leaking it to callers.

``reconcile_item`` is the integrity check (D16): the ledger sum must equal the
denormalised on-hand balance.
"""
import uuid
from decimal import Decimal
from typing import Optional

from django.db import transaction

from contexts.inventory.domain.enums import StockMovementType
from contexts.inventory.events import publish_stock_consumed
from contexts.inventory.exceptions import (
    InsufficientStock,
    InventoryItemNotFound,
    ValidationError,
)
from contexts.inventory.models import StockMovement
from contexts.inventory.repositories import (
    BatchRepository,
    InventoryItemRepository,
    StockMovementRepository,
)
from contexts.inventory.services.movement_service import apply_stock_movement

_items = InventoryItemRepository()
_batches = BatchRepository()
_movements = StockMovementRepository()


@transaction.atomic
def consume_stock(
    *,
    inventory_item_id: uuid.UUID,
    quantity: Decimal,
    movement_type: StockMovementType = StockMovementType.SALE,
    reference_type: str = "",
    reference_id: Optional[uuid.UUID] = None,
    reference_number: str = "",
    performed_by_id: Optional[uuid.UUID] = None,
    idempotency_key: str = "",
    allow_negative: bool = False,
) -> list[StockMovement]:
    """Deduct ``quantity`` (positive) from an item, FEFO across its batches.

    Returns the movements created (one per batch consumed). Idempotent: a
    redelivered call with the same ``idempotency_key`` returns the prior result
    without deducting again.
    """
    if quantity <= 0:
        raise ValidationError({"quantity": "Consumption quantity must be positive."})

    # Idempotency: the first movement of a prior run carries the key.
    if idempotency_key and _movements.by_key(idempotency_key) is not None:
        if reference_type and reference_id is not None:
            return list(_movements.for_reference(reference_type, reference_id))
        return [_movements.by_key(idempotency_key)]

    item = _items.lock(inventory_item_id)
    if item is None:
        raise InventoryItemNotFound(str(inventory_item_id))
    if quantity > item.quantity_on_hand and not allow_negative:
        raise InsufficientStock(item.product_sku, item.quantity_on_hand, quantity)

    movements: list[StockMovement] = []
    remaining = quantity
    first = True

    for batch in _batches.lock_fefo_batches(inventory_item_id):
        if remaining <= 0:
            break
        take = min(remaining, batch.quantity)
        if take <= 0:
            continue
        movements.append(_post(
            item_id=inventory_item_id, qty=-take, movement_type=movement_type,
            batch_id=batch.id, reference_type=reference_type,
            reference_id=reference_id, reference_number=reference_number,
            performed_by_id=performed_by_id,
            idempotency_key=idempotency_key if first else "",
            allow_negative=allow_negative,
        ))
        remaining -= take
        first = False

    # Untracked remainder (no batches, or batch sum < on-hand) — post directly.
    if remaining > 0:
        movements.append(_post(
            item_id=inventory_item_id, qty=-remaining, movement_type=movement_type,
            batch_id=None, reference_type=reference_type,
            reference_id=reference_id, reference_number=reference_number,
            performed_by_id=performed_by_id,
            idempotency_key=idempotency_key if first else "",
            allow_negative=allow_negative,
        ))

    publish_stock_consumed(
        inventory_item_id=inventory_item_id,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    return movements


def _post(*, item_id, qty, movement_type, batch_id, reference_type,
          reference_id, reference_number, performed_by_id,
          idempotency_key, allow_negative) -> StockMovement:
    return apply_stock_movement(
        inventory_item_id=item_id,
        movement_type=movement_type,
        quantity=qty,
        batch_id=batch_id,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        performed_by_id=performed_by_id,
        idempotency_key=idempotency_key,
        allow_negative=allow_negative,
    )


def reconcile_item(inventory_item_id: uuid.UUID) -> dict:
    """Compare the denormalised on-hand balance with the ledger sum.

    ``ok`` is True when they agree; ``discrepancy`` is on_hand − ledger.
    """
    item = _items.get(inventory_item_id)
    if item is None:
        raise InventoryItemNotFound(str(inventory_item_id))
    ledger_balance = _movements.balance_sum(inventory_item_id)
    discrepancy = item.quantity_on_hand - ledger_balance
    return {
        "inventory_item_id": inventory_item_id,
        "on_hand": item.quantity_on_hand,
        "ledger_balance": ledger_balance,
        "discrepancy": discrepancy,
        "ok": discrepancy == Decimal("0"),
    }
