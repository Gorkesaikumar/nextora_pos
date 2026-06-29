"""Purchase Order service — lifecycle management for supplier orders.

Reads/locks go through repositories; stock effects go through the ledger
(`apply_stock_movement`). Receipts create batches, post PURCHASE movements
(which update weighted-average cost), and decrement ``quantity_on_order``.
"""
import uuid
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction

from contexts.inventory.domain.enums import (
    PurchaseOrderStatus,
    StockMovementType,
)
from contexts.inventory.exceptions import (
    InvalidStateTransition,
    PurchaseOrderLineNotFound,
    PurchaseOrderNotFound,
    ValidationError,
)
from contexts.inventory.models import Batch, PurchaseOrder, PurchaseOrderLine
from contexts.inventory.repositories import (
    InventoryItemRepository,
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
)
from contexts.inventory.events import publish_stock_received
from contexts.inventory.services import numbering
from contexts.inventory.services.audit import audit_event
from contexts.inventory.services.movement_service import apply_stock_movement

_pos = PurchaseOrderRepository()
_po_lines = PurchaseOrderLineRepository()
_items = InventoryItemRepository()


@transaction.atomic
def create_purchase_order(
    *,
    tenant_id: uuid.UUID,
    supplier_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lines: list[dict[str, Any]],
    expected_delivery_date=None,
    notes: str = "",
) -> PurchaseOrder:
    """Create a DRAFT purchase order with validated line items.

    ``lines``: dicts of ``inventory_item_id``, ``quantity_ordered``,
    ``unit_cost``, optional ``tax_rate``.
    """
    if not lines:
        raise ValidationError({"lines": "A purchase order needs at least one line."})

    po = _pos.add(PurchaseOrder(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        order_number=numbering.next_document_number(
            numbering.SCOPE_PURCHASE_ORDER, "PO"
        ),
        status=PurchaseOrderStatus.DRAFT,
        expected_delivery_date=expected_delivery_date,
        notes=notes,
    ))

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for line_data in lines:
        qty = Decimal(str(line_data["quantity_ordered"]))
        cost = Decimal(str(line_data["unit_cost"]))
        tax_rate = Decimal(str(line_data.get("tax_rate", "0")))
        line_subtotal = qty * cost
        line_tax = line_subtotal * tax_rate

        _po_lines.add(PurchaseOrderLine(
            tenant_id=tenant_id,
            purchase_order=po,
            inventory_item_id=line_data["inventory_item_id"],
            quantity_ordered=qty,
            unit_cost=cost,
            tax_rate=tax_rate,
            line_total=line_subtotal + line_tax,
        ))
        subtotal += line_subtotal
        tax_total += line_tax

    po.subtotal = subtotal
    po.tax_amount = tax_total
    po.total_amount = subtotal + tax_total
    _pos.save(po, update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])

    audit_event(
        "purchase_order.created",
        entity_type="purchase_order",
        entity_id=po.id,
        values={
            "order_number": po.order_number,
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "line_count": len(lines),
            "total_amount": po.total_amount,
        },
    )
    return po


@transaction.atomic
def receive_purchase_order(
    *,
    purchase_order_id: uuid.UUID,
    receipts: list[dict[str, Any]],
    received_by_id: Optional[uuid.UUID] = None,
) -> PurchaseOrder:
    """Record stock received against a purchase order (supports partial receipts).

    ``receipts``: dicts of ``line_id``, ``quantity_received``, optional
    ``batch_number``/``expiry_date``/``manufacture_date``.
    """
    po = _pos.lock(purchase_order_id)
    if po is None:
        raise PurchaseOrderNotFound(str(purchase_order_id))
    if po.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
        raise InvalidStateTransition("purchase order", po.status, "receive against")

    for receipt in receipts:
        line = _po_lines.lock(receipt["line_id"])
        if line is None:
            raise PurchaseOrderLineNotFound(str(receipt["line_id"]))

        qty = Decimal(str(receipt["quantity_received"]))
        if qty <= 0:
            continue

        remaining = line.quantity_ordered - line.quantity_received
        if qty > remaining:
            raise ValidationError({
                "quantity_received": (
                    f"Received {qty} exceeds remaining order quantity {remaining} "
                    f"for {line.inventory_item.product_sku}."
                )
            })

        batch = None
        batch_number = receipt.get("batch_number")
        if batch_number:
            batch, _ = Batch.objects.get_or_create(
                inventory_item=line.inventory_item,
                batch_number=batch_number,
                defaults={
                    "tenant": po.tenant,
                    "expiry_date": receipt.get("expiry_date"),
                    "manufacture_date": receipt.get("manufacture_date"),
                    "unit_cost": line.unit_cost,
                    "purchase_order_id": po.id,
                    "quantity": 0,
                },
            )

        apply_stock_movement(
            inventory_item_id=line.inventory_item_id,
            movement_type=StockMovementType.PURCHASE,
            quantity=qty,
            unit_cost=line.unit_cost,
            batch_id=batch.id if batch else None,
            reference_type="purchase_order",
            reference_id=po.id,
            reference_number=po.order_number,
            performed_by_id=received_by_id,
        )

        line.quantity_received += qty
        _po_lines.save(line, update_fields=["quantity_received", "updated_at"])

        item = _items.get(line.inventory_item_id)
        if item is not None:
            item.quantity_on_order = max(Decimal("0"), item.quantity_on_order - qty)
            _items.save(item, update_fields=["quantity_on_order", "updated_at"])

        publish_stock_received(
            inventory_item_id=line.inventory_item_id,
            warehouse_id=po.warehouse_id,
            quantity=qty,
            unit_cost=line.unit_cost,
            reference_type="purchase_order",
            reference_id=po.id,
            reference_number=po.order_number,
        )

    # Recalculate PO status from line fulfilment.
    lines = list(po.lines.all())
    if all(ln.quantity_received >= ln.quantity_ordered for ln in lines):
        po.status = PurchaseOrderStatus.RECEIVED
    elif any(ln.quantity_received > 0 for ln in lines):
        po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    _pos.save(po, update_fields=["status", "updated_at"])

    audit_event(
        "purchase_order.received",
        entity_type="purchase_order",
        entity_id=po.id,
        values={
            "order_number": po.order_number,
            "status": po.status,
            "receipt_lines": len(receipts),
        },
    )
    return po
