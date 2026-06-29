"""Stock adjustment service — manual corrections and damaged-goods write-offs.

Adjustments capture a target quantity per line; approval applies the signed
delta through the ledger. Damage is a first-class record that also drives an
auto-approved write-off adjustment for full traceability.
"""
import uuid
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from contexts.inventory.domain.enums import StockMovementType
from contexts.inventory.exceptions import (
    AdjustmentNotFound,
    InvalidStateTransition,
    InventoryItemNotFound,
)
from contexts.inventory.models import (
    DamagedStock,
    StockAdjustment,
    StockAdjustmentLine,
)
from contexts.inventory.models.adjustment import AdjustmentReason
from contexts.inventory.repositories import (
    DamagedStockRepository,
    InventoryItemRepository,
    StockAdjustmentLineRepository,
    StockAdjustmentRepository,
)
from contexts.inventory.events import publish_stock_adjusted
from contexts.inventory.services import numbering
from contexts.inventory.services.audit import audit_event
from contexts.inventory.services.movement_service import apply_stock_movement

_adjustments = StockAdjustmentRepository()
_adj_lines = StockAdjustmentLineRepository()
_damaged = DamagedStockRepository()
_items = InventoryItemRepository()

# Reason → outgoing movement type (incoming deltas are always ADJUSTMENT_ADD).
_REMOVE_TYPE_BY_REASON = {
    AdjustmentReason.DAMAGED: StockMovementType.DAMAGED,
    AdjustmentReason.EXPIRED: StockMovementType.DAMAGED,
    AdjustmentReason.THEFT: StockMovementType.ADJUSTMENT_REMOVE,
}


@transaction.atomic
def create_adjustment(
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    reason: AdjustmentReason,
    lines: list[dict[str, Any]],
    notes: str = "",
    adjusted_by_id: Optional[uuid.UUID] = None,
) -> StockAdjustment:
    """Create a (not-yet-approved) adjustment.

    ``lines``: dicts of ``inventory_item_id``, ``quantity_after`` (target qty),
    optional ``batch_id``.
    """
    adjustment = _adjustments.add(StockAdjustment(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        adjustment_number=numbering.next_document_number(
            numbering.SCOPE_ADJUSTMENT, "ADJ"
        ),
        reason=reason,
        notes=notes,
        adjusted_by_id=adjusted_by_id,
    ))

    for line_data in lines:
        item = _items.get(line_data["inventory_item_id"])
        if item is None:
            raise InventoryItemNotFound(str(line_data["inventory_item_id"]))

        _adj_lines.add(StockAdjustmentLine(
            tenant_id=tenant_id,
            adjustment=adjustment,
            inventory_item=item,
            batch_id=line_data.get("batch_id"),
            quantity_before=item.quantity_on_hand,
            quantity_after=Decimal(str(line_data["quantity_after"])),
            unit_cost=item.average_cost,
        ))

    audit_event(
        "stock_adjustment.created",
        entity_type="stock_adjustment",
        entity_id=adjustment.id,
        values={
            "adjustment_number": adjustment.adjustment_number,
            "reason": reason,
            "warehouse_id": warehouse_id,
            "line_count": len(lines),
        },
    )
    return adjustment


@transaction.atomic
def approve_and_apply_adjustment(
    adjustment_id: uuid.UUID,
    approved_by_id: Optional[uuid.UUID] = None,
) -> StockAdjustment:
    """Approve an adjustment and post a signed StockMovement per changed line."""
    adjustment = _adjustments.lock(adjustment_id)
    if adjustment is None:
        raise AdjustmentNotFound(str(adjustment_id))
    if adjustment.is_approved:
        raise InvalidStateTransition("adjustment", "approved", "re-approve")

    for line in _adj_lines.for_adjustment(adjustment.id):
        delta = line.quantity_after - line.quantity_before
        if delta == 0:
            continue
        mvt_type = (
            StockMovementType.ADJUSTMENT_ADD if delta > 0
            else _REMOVE_TYPE_BY_REASON.get(
                adjustment.reason, StockMovementType.ADJUSTMENT_REMOVE
            )
        )
        apply_stock_movement(
            inventory_item_id=line.inventory_item_id,
            movement_type=mvt_type,
            quantity=delta,
            unit_cost=line.unit_cost,
            batch_id=line.batch_id,
            reference_type="adjustment",
            reference_id=adjustment.id,
            reference_number=adjustment.adjustment_number,
            performed_by_id=approved_by_id,
            notes=adjustment.notes,
        )

    adjustment.is_approved = True
    adjustment.approved_by_id = approved_by_id
    adjustment.approved_at = timezone.now()
    _adjustments.save(
        adjustment,
        update_fields=["is_approved", "approved_by_id", "approved_at", "updated_at"],
    )

    audit_event(
        "stock_adjustment.approved",
        entity_type="stock_adjustment",
        entity_id=adjustment.id,
        values={
            "adjustment_number": adjustment.adjustment_number,
            "reason": adjustment.reason,
            "approved_by_id": approved_by_id,
        },
    )
    publish_stock_adjusted(
        adjustment_id=adjustment.id,
        adjustment_number=adjustment.adjustment_number,
        reason=adjustment.reason,
    )
    return adjustment


@transaction.atomic
def record_damaged_stock(
    *,
    tenant_id: uuid.UUID,
    inventory_item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: Decimal,
    damage_reason: str,
    incident_date,
    batch_id: Optional[uuid.UUID] = None,
    reported_by_id: Optional[uuid.UUID] = None,
    image=None,
) -> DamagedStock:
    """Record damaged/spoiled stock and immediately write it off.

    Creates an auto-approved DAMAGED adjustment plus a DamagedStock record
    (for insurance/compliance) linked to that adjustment.
    """
    item = _items.get(inventory_item_id)
    if item is None:
        raise InventoryItemNotFound(str(inventory_item_id))

    adjustment = create_adjustment(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        reason=AdjustmentReason.DAMAGED,
        lines=[{
            "inventory_item_id": inventory_item_id,
            "quantity_after": item.quantity_on_hand - quantity,
            "batch_id": batch_id,
        }],
        notes=f"Damage write-off: {damage_reason}",
        adjusted_by_id=reported_by_id,
    )
    approve_and_apply_adjustment(adjustment.id, approved_by_id=reported_by_id)

    damaged = _damaged.add(DamagedStock(
        tenant_id=tenant_id,
        inventory_item_id=inventory_item_id,
        batch_id=batch_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        unit_cost=item.average_cost,
        damage_reason=damage_reason,
        incident_date=incident_date,
        reported_by_id=reported_by_id,
        adjustment=adjustment,
        image=image,
    ))

    audit_event(
        "stock.damaged",
        entity_type="damaged_stock",
        entity_id=damaged.id,
        values={
            "inventory_item_id": inventory_item_id,
            "warehouse_id": warehouse_id,
            "quantity": quantity,
            "loss_value": damaged.total_loss_value,
            "adjustment_number": adjustment.adjustment_number,
        },
        reason=damage_reason,
    )
    return damaged
