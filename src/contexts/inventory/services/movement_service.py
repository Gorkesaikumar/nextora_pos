"""Stock movement service — the single source of truth for all stock mutations.

Every quantity change MUST go through ``apply_stock_movement``. It:
  1. Returns early if the operation's idempotency key was already applied
     (exactly-once for at-least-once callers — redelivered events / retried tasks).
  2. Row-locks the InventoryItem (``SELECT … FOR UPDATE``) so concurrent changes
     serialise and balances never get lost.
  3. Enforces the non-negative policy (unless ``allow_negative``).
  4. Updates batch quantity (if batch-tracked).
  5. Recomputes weighted-average cost on stock-in — correctly even when the
     prior balance was zero/negative (ADR-0001 review A2).
  6. Appends the immutable StockMovement ledger row.
  7. Schedules alert evaluation after commit.
"""
import uuid
from decimal import Decimal
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from contexts.inventory.domain.enums import AlertStatus, AlertType, StockMovementType
from contexts.inventory.events import publish_low_stock_detected
from contexts.inventory.exceptions import (
    InsufficientStock,
    InventoryItemNotFound,
)
from contexts.inventory.models import InventoryAlert, StockMovement
from contexts.inventory.repositories import (
    BatchRepository,
    InventoryItemRepository,
    StockMovementRepository,
)

_items = InventoryItemRepository()
_batches = BatchRepository()
_movements = StockMovementRepository()

_COST_QUANT = Decimal("0.0001")  # average_cost has 4 decimal places


@transaction.atomic
def apply_stock_movement(
    *,
    inventory_item_id: uuid.UUID,
    movement_type: StockMovementType,
    quantity: Decimal,
    unit_cost: Decimal = Decimal("0"),
    batch_id: Optional[uuid.UUID] = None,
    reference_type: str = "",
    reference_id: Optional[uuid.UUID] = None,
    reference_number: str = "",
    notes: str = "",
    performed_by_id: Optional[uuid.UUID] = None,
    idempotency_key: str = "",
    allow_negative: bool = False,
) -> StockMovement:
    """Apply a signed quantity change to an InventoryItem.

    ``quantity`` is signed: positive = stock in, negative = stock out.

    Raises:
        InventoryItemNotFound: the item does not exist for the current tenant.
        InsufficientStock: the change would go below zero and ``allow_negative``
            is False.
    """
    # 1. Idempotency fast-path (the DB constraint is the race-proof backstop).
    if idempotency_key:
        existing = _movements.by_key(idempotency_key)
        if existing is not None:
            return existing

    # 2-5. Apply the whole mutation in a savepoint so an idempotency-race
    # collision on the ledger insert rolls back the item/batch updates too
    # (otherwise a lost race would double-apply stock).
    try:
        with transaction.atomic():
            item = _items.lock(inventory_item_id)
            if item is None:
                raise InventoryItemNotFound(str(inventory_item_id))

            old_balance = item.quantity_on_hand
            new_balance = old_balance + quantity
            if new_balance < 0 and not allow_negative:
                raise InsufficientStock(item.product_sku, old_balance, abs(quantity))

            batch = None
            if batch_id:
                batch = _batches.lock(batch_id)
                if batch is None:
                    raise InventoryItemNotFound(f"Batch {batch_id} not found.")
                batch_new_qty = batch.quantity + quantity
                if batch_new_qty < 0 and not allow_negative:
                    raise InsufficientStock(
                        f"{item.product_sku} batch {batch.batch_number}",
                        batch.quantity, abs(quantity),
                    )
                batch.quantity = batch_new_qty
                _batches.save(batch, update_fields=["quantity", "updated_at"])

            item.quantity_on_hand = new_balance
            if quantity > 0 and unit_cost > 0:
                item.average_cost = _recompute_wac(
                    old_balance, item.average_cost, quantity, unit_cost, new_balance
                )
            _items.save(
                item, update_fields=["quantity_on_hand", "average_cost", "updated_at"]
            )

            movement = StockMovement.objects.create(
                tenant=item.tenant,
                inventory_item=item,
                batch=batch,
                movement_type=movement_type,
                quantity=quantity,
                unit_cost=unit_cost,
                balance_after=new_balance,
                reference_type=reference_type,
                reference_id=reference_id,
                reference_number=reference_number,
                notes=notes,
                performed_by_id=performed_by_id,
                idempotency_key=idempotency_key,
            )
    except IntegrityError:
        # Lost the race on uq_movement__idempotency — another worker applied it.
        # The savepoint rolled back our duplicate item/batch updates.
        existing = _movements.by_key(idempotency_key) if idempotency_key else None
        if existing is not None:
            return existing
        raise

    # 6. Evaluate stock-level alerts after the write commits.
    transaction.on_commit(lambda: _check_and_fire_alerts(inventory_item_id))
    return movement


def _recompute_wac(
    old_balance: Decimal,
    old_avg: Decimal,
    quantity: Decimal,
    unit_cost: Decimal,
    new_balance: Decimal,
) -> Decimal:
    """Weighted-average cost on stock-in.

    When the prior balance was zero or negative (back-ordered / oversold), the
    classic weighted formula divides by a small/garbage base and corrupts the
    average (ADR-0001 review A2). In that case fall back to the last cost.
    """
    if old_balance <= 0 or new_balance <= 0:
        return unit_cost.quantize(_COST_QUANT)
    total_value = old_balance * old_avg + quantity * unit_cost
    return (total_value / new_balance).quantize(_COST_QUANT)


def _check_and_fire_alerts(inventory_item_id: uuid.UUID) -> None:
    """Re-evaluate stock-level alerts for an item (runs in its own transaction).

    The item is re-locked so two concurrent evaluations can't make inconsistent
    create-vs-resolve decisions on a stale read (ADR-0001 review R2).
    """
    with transaction.atomic():
        item = _items.get_queryset().select_for_update().filter(
            id=inventory_item_id, is_active=True
        ).first()
        if item is None:
            return
        _evaluate_low_stock_alert(item)


def _evaluate_low_stock_alert(item) -> None:
    """Create LOW_STOCK / OUT_OF_STOCK or auto-resolve when the level recovers."""
    if item.minimum_stock <= 0:
        return

    if item.quantity_on_hand <= 0:
        _raise_alert(
            item, AlertType.OUT_OF_STOCK,
            message=f"{item.product_name} is out of stock.",
            out_of_stock=True,
            quantity_at_alert=item.quantity_on_hand,
            threshold_value=item.minimum_stock,
        )
    elif item.quantity_on_hand <= item.minimum_stock:
        _raise_alert(
            item, AlertType.LOW_STOCK,
            message=(
                f"{item.product_name} is below minimum stock. "
                f"On hand: {item.quantity_on_hand}, Minimum: {item.minimum_stock}"
            ),
            out_of_stock=False,
            quantity_at_alert=item.quantity_on_hand,
            threshold_value=item.minimum_stock,
        )
    else:
        InventoryAlert.objects.filter(
            inventory_item=item,
            alert_type__in=[AlertType.LOW_STOCK, AlertType.OUT_OF_STOCK],
            status=AlertStatus.OPEN,
        ).update(status=AlertStatus.RESOLVED, resolved_at=timezone.now())


def _raise_alert(
    item, alert_type: AlertType, message: str, *, out_of_stock: bool, **kwargs
) -> InventoryAlert:
    """Create the alert (idempotent) and publish LowStockDetected on first raise."""
    alert, created = InventoryAlert.objects.get_or_create(
        inventory_item=item,
        alert_type=alert_type,
        status=AlertStatus.OPEN,
        defaults={"tenant": item.tenant, "message": message, **kwargs},
    )
    if created:
        # Emit only on a fresh alert so subscribers (reorder, notifications)
        # aren't spammed on every movement while the condition persists.
        publish_low_stock_detected(
            inventory_item_id=item.id,
            warehouse_id=item.warehouse_id,
            product_sku=item.product_sku,
            quantity_on_hand=item.quantity_on_hand,
            minimum_stock=item.minimum_stock,
            out_of_stock=out_of_stock,
        )
    return alert
