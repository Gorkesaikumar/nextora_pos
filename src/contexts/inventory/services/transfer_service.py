"""Transfer service — inter-warehouse stock movements.

Two-phase: dispatch posts TRANSFER_OUT at the source, receipt posts TRANSFER_IN
at the destination. Lines are processed in ``inventory_item_id`` order so locks
are always acquired deterministically (deadlock avoidance — ADR-0001 review R3).

Note: in-transit stock is not yet modelled as its own bucket (ADR-0001 review
W1); between dispatch and receipt the quantity is decremented at source only.
"""
import uuid
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from contexts.inventory.domain.enums import StockMovementType, TransferStatus
from contexts.inventory.exceptions import (
    InvalidStateTransition,
    InventoryItemNotFound,
    TransferNotFound,
    ValidationError,
)
from contexts.inventory.models import StockTransfer, StockTransferLine
from contexts.inventory.repositories import (
    InventoryItemRepository,
    StockTransferLineRepository,
    StockTransferRepository,
)
from contexts.inventory.events import publish_stock_transferred
from contexts.inventory.services import numbering
from contexts.inventory.services.audit import audit_event
from contexts.inventory.services.movement_service import apply_stock_movement

_transfers = StockTransferRepository()
_transfer_lines = StockTransferLineRepository()
_items = InventoryItemRepository()


@transaction.atomic
def create_transfer(
    *,
    tenant_id: uuid.UUID,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    lines: list[dict[str, Any]],
    expected_date=None,
    notes: str = "",
) -> StockTransfer:
    """Create a DRAFT inter-warehouse transfer.

    ``lines``: dicts of ``inventory_item_id``, ``quantity_requested``, optional
    ``batch_id``.
    """
    if from_warehouse_id == to_warehouse_id:
        raise ValidationError(
            {"to_warehouse": "Source and destination warehouse must differ."}
        )
    if not lines:
        raise ValidationError({"lines": "A transfer needs at least one line."})

    transfer = _transfers.add(StockTransfer(
        tenant_id=tenant_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        transfer_number=numbering.next_document_number(
            numbering.SCOPE_TRANSFER, "TRF"
        ),
        status=TransferStatus.DRAFT,
        expected_date=expected_date,
        notes=notes,
    ))

    for line_data in lines:
        _transfer_lines.add(StockTransferLine(
            tenant_id=tenant_id,
            transfer=transfer,
            inventory_item_id=line_data["inventory_item_id"],
            batch_id=line_data.get("batch_id"),
            quantity_requested=Decimal(str(line_data["quantity_requested"])),
        ))

    audit_event(
        "stock_transfer.created",
        entity_type="stock_transfer",
        entity_id=transfer.id,
        values={
            "transfer_number": transfer.transfer_number,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "line_count": len(lines),
        },
    )
    return transfer


@transaction.atomic
def dispatch_transfer(
    transfer_id: uuid.UUID,
    dispatched_by_id: Optional[uuid.UUID] = None,
) -> StockTransfer:
    """Mark IN_TRANSIT and deduct stock from the source warehouse."""
    transfer = _transfers.lock(transfer_id)
    if transfer is None:
        raise TransferNotFound(str(transfer_id))
    if transfer.status != TransferStatus.DRAFT:
        raise InvalidStateTransition("transfer", transfer.status, "dispatch")

    for line in _transfer_lines.for_transfer(transfer.id):
        apply_stock_movement(
            inventory_item_id=line.inventory_item_id,
            movement_type=StockMovementType.TRANSFER_OUT,
            quantity=-line.quantity_requested,
            batch_id=line.batch_id,
            reference_type="transfer",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            performed_by_id=dispatched_by_id,
        )
        line.quantity_dispatched = line.quantity_requested
        _transfer_lines.save(line, update_fields=["quantity_dispatched", "updated_at"])

    transfer.status = TransferStatus.IN_TRANSIT
    transfer.dispatched_at = timezone.now()
    transfer.dispatched_by_id = dispatched_by_id
    _transfers.save(
        transfer,
        update_fields=["status", "dispatched_at", "dispatched_by_id", "updated_at"],
    )

    audit_event(
        "stock_transfer.dispatched",
        entity_type="stock_transfer",
        entity_id=transfer.id,
        values={"transfer_number": transfer.transfer_number},
    )
    return transfer


@transaction.atomic
def receive_transfer(
    transfer_id: uuid.UUID,
    received_by_id: Optional[uuid.UUID] = None,
) -> StockTransfer:
    """Confirm receipt at the destination; posts TRANSFER_IN movements."""
    transfer = _transfers.lock(transfer_id)
    if transfer is None:
        raise TransferNotFound(str(transfer_id))
    if transfer.status != TransferStatus.IN_TRANSIT:
        raise InvalidStateTransition("transfer", transfer.status, "receive")

    for line in _transfer_lines.for_transfer(transfer.id):
        dest_item = _items.get_for_product_warehouse(
            line.inventory_item.product_id, transfer.to_warehouse_id
        )
        if dest_item is None:
            raise InventoryItemNotFound(
                f"No stock record for {line.inventory_item.product_sku} "
                f"in destination warehouse {transfer.to_warehouse_id}."
            )

        apply_stock_movement(
            inventory_item_id=dest_item.id,
            movement_type=StockMovementType.TRANSFER_IN,
            quantity=line.quantity_dispatched,
            unit_cost=line.inventory_item.average_cost,
            batch_id=line.batch_id,
            reference_type="transfer",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            performed_by_id=received_by_id,
        )
        line.quantity_received = line.quantity_dispatched
        _transfer_lines.save(line, update_fields=["quantity_received", "updated_at"])

    transfer.status = TransferStatus.RECEIVED
    transfer.received_at = timezone.now()
    transfer.received_by_id = received_by_id
    _transfers.save(
        transfer,
        update_fields=["status", "received_at", "received_by_id", "updated_at"],
    )

    audit_event(
        "stock_transfer.received",
        entity_type="stock_transfer",
        entity_id=transfer.id,
        values={"transfer_number": transfer.transfer_number},
    )
    publish_stock_transferred(
        transfer_id=transfer.id,
        transfer_number=transfer.transfer_number,
        from_warehouse_id=transfer.from_warehouse_id,
        to_warehouse_id=transfer.to_warehouse_id,
    )
    return transfer
