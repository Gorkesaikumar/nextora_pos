"""Order operations: create, add items, discount, split, merge, void, recalc.

All mutations are atomic and lock the order row where concurrent edits matter.
Recalculation re-derives the full bill snapshot from the active line items.
"""
import uuid
from decimal import Decimal

from django.db import transaction

from contexts.audit.services import record_audit
from contexts.catalog.services.product_service import resolve_routing
from contexts.ordering.domain.billing import BillLine, compute_bill
from contexts.ordering.domain.enums import (
    DiscountType,
    ItemStatus,
    OrderStatus,
)
from contexts.ordering.domain.finance import q
from contexts.ordering.exceptions import OrderNotOpen
from contexts.ordering.models import Order, OrderItem, OrderItemModifier
from contexts.ordering.services import sequences
from contexts.ordering.realtime import broadcast_tenant_event


def _locked(order_id: uuid.UUID) -> Order:
    return Order.objects.select_for_update().get(id=order_id)


def create_order(
    *,
    location_id: uuid.UUID,
    order_type: str,
    table_id: uuid.UUID | None = None,
    is_interstate: bool = False,
    service_charge_rate: Decimal = Decimal("0"),
    created_by: uuid.UUID | None = None,
) -> Order:
    with transaction.atomic():
        number = sequences.next_number(location_id, "order")
        order = Order.objects.create(
            location_id=location_id,
            order_number=f"{number:04d}",
            table_id=table_id,
            type=order_type,
            is_interstate=is_interstate,
            service_charge_rate=service_charge_rate,
            created_by=created_by,
        )
    record_audit("order.created", entity_type="order", entity_id=order.id)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return order


def _refresh_item_totals(item: OrderItem) -> None:
    item.line_subtotal = q(item.qty * item.unit_price + item.modifiers_total)
    item.line_total = q(item.line_subtotal - item.line_discount)


@transaction.atomic
def add_item(
    order_id: uuid.UUID,
    product,
    *,
    variant=None,
    qty: Decimal = Decimal("1"),
    modifiers=None,
    notes: str = "",
) -> OrderItem:
    order = _locked(order_id)
    if order.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))

    modifiers = modifiers or []
    unit_price = product.base_price + (variant.price_delta if variant else Decimal("0"))
    tax_rate = product.tax_class.gst_rate if product.tax_class else Decimal("0")
    cess_rate = product.tax_class.cess_rate if product.tax_class else Decimal("0")
    _, station = resolve_routing(product)
    name = product.name + (f" ({variant.name})" if variant else "")

    modifiers_total = q(sum((m.price_delta for m in modifiers), Decimal("0")))
    item = OrderItem(
        order=order, product_id=product.id,
        variant_id=variant.id if variant else None,
        name_snapshot=name, qty=Decimal(qty), unit_price=unit_price,
        modifiers_total=modifiers_total, tax_rate=tax_rate, cess_rate=cess_rate,
        hsn_code=getattr(product, "hsn_code", ""),
        kitchen_station_id=station.id if station else None,
        notes=notes,
    )
    _refresh_item_totals(item)
    item.save()

    for modifier in modifiers:
        OrderItemModifier.objects.create(
            item=item, modifier_id=modifier.id,
            name_snapshot=modifier.name, price_delta=modifier.price_delta,
        )

    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return item


@transaction.atomic
def set_item_qty(order_id: uuid.UUID, item_id: uuid.UUID, qty: Decimal) -> OrderItem:
    """Set the quantity of an order item and recompute line + order totals."""
    order = _locked(order_id)
    if order.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))
    item = order.items.get(id=item_id, status=ItemStatus.ACTIVE)
    if qty <= 0:
        item.status = ItemStatus.VOID
        item.save(update_fields=["status", "updated_at"])
    else:
        item.qty = qty
        _refresh_item_totals(item)
        item.save()
    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return item


def void_item(order_id: uuid.UUID, item_id: uuid.UUID) -> None:
    with transaction.atomic():
        order = _locked(order_id)
        item = order.items.get(id=item_id)
        item.status = ItemStatus.VOID
        item.save(update_fields=["status", "updated_at"])
        recalculate(order)
    record_audit("order.item_voided", entity_type="order", entity_id=order_id,
                 changes={"item_id": str(item_id)})
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))


def apply_discount(order_id: uuid.UUID, discount_type: str, value: Decimal) -> Order:
    with transaction.atomic():
        order = _locked(order_id)
        if order.status != OrderStatus.OPEN:
            raise OrderNotOpen(str(order_id))
        order.discount_type = discount_type
        order.discount_value = q(value)
        recalculate(order)
    return order


def set_service_charge(order_id: uuid.UUID, rate: Decimal) -> Order:
    with transaction.atomic():
        order = _locked(order_id)
        order.service_charge_rate = q(rate)
        recalculate(order)
    return order


def recalculate(order: Order) -> Order:
    """Re-derive the bill snapshot from active items and persist it."""
    items = list(order.items.filter(status=ItemStatus.ACTIVE))
    subtotal = q(sum((i.line_total for i in items), Decimal("0")))

    if order.discount_type == DiscountType.PERCENT:
        discount = q(subtotal * order.discount_value / Decimal("100"))
    elif order.discount_type == DiscountType.FLAT:
        discount = q(min(order.discount_value, subtotal))
    else:
        discount = Decimal("0.00")

    breakup = compute_bill(
        [BillLine(i.line_total, i.tax_rate, i.cess_rate) for i in items],
        order_discount=discount,
        service_charge_rate=order.service_charge_rate,
        interstate=order.is_interstate,
    )

    order.subtotal = breakup.subtotal
    order.discount_amount = breakup.discount
    order.service_charge_amount = breakup.service_charge
    order.taxable_amount = breakup.taxable
    order.cgst, order.sgst, order.igst, order.cess = (
        breakup.cgst, breakup.sgst, breakup.igst, breakup.cess
    )
    order.tax_amount = breakup.tax_total
    order.round_off = breakup.round_off
    order.total = breakup.total
    order.due_amount = q(order.total - order.paid_amount)
    order.save()
    
    try:
        from django.db import transaction
        from shared.tenancy.context import get_current_tenant
        tid = get_current_tenant()
        transaction.on_commit(lambda: broadcast_tenant_event("order_changed", tenant_id=tid))
    except Exception:
        pass
        
    return order


# --- Split / Merge ---------------------------------------------------------
@transaction.atomic
def split_order(order_id: uuid.UUID, moves: list[dict]) -> Order:
    """Move selected items (optionally partial qty) onto a new bill.

    moves = [{"item_id": <uuid>, "qty": <Decimal optional>}]
    """
    source = _locked(order_id)
    if source.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))

    target = Order.objects.create(
        location_id=source.location_id,
        order_number=f"{sequences.next_number(source.location_id, 'order'):04d}",
        type=source.type, is_interstate=source.is_interstate,
        service_charge_rate=source.service_charge_rate,
        table_id=source.table_id, split_from=source,
    )

    for move in moves:
        item = source.items.get(id=move["item_id"], status=ItemStatus.ACTIVE)
        move_qty = Decimal(move.get("qty") or item.qty)
        if move_qty >= item.qty:
            item.order = target
            item.save(update_fields=["order", "updated_at"])
        else:
            # Partial: reduce source line, clone the remainder onto target.
            item.qty = item.qty - move_qty
            _refresh_item_totals(item)
            item.save()
            clone = OrderItem(
                order=target, product_id=item.product_id,
                variant_id=item.variant_id, name_snapshot=item.name_snapshot,
                qty=move_qty, unit_price=item.unit_price,
                modifiers_total=item.modifiers_total, tax_rate=item.tax_rate,
                cess_rate=item.cess_rate, hsn_code=item.hsn_code,
                kitchen_station_id=item.kitchen_station_id, notes=item.notes,
            )
            _refresh_item_totals(clone)
            clone.save()

    recalculate(source)
    recalculate(target)
    record_audit("order.split", entity_type="order", entity_id=source.id,
                 changes={"target": str(target.id)})
    return target


@transaction.atomic
def merge_orders(target_id: uuid.UUID, source_ids: list[uuid.UUID]) -> Order:
    """Move all active items from sources into the target and close the sources."""
    target = _locked(target_id)
    if target.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(target_id))

    for source_id in source_ids:
        source = _locked(source_id)
        if source.status != OrderStatus.OPEN:
            raise OrderNotOpen(str(source_id))
        source.items.filter(status=ItemStatus.ACTIVE).update(order=target)
        source.merged_into = target
        source.status = OrderStatus.VOID
        recalculate(source)  # source now has no active items -> zeroed
        source.save(update_fields=["merged_into", "status", "updated_at"])

    recalculate(target)
    record_audit("order.merged", entity_type="order", entity_id=target.id,
                 changes={"sources": [str(s) for s in source_ids]})
    return target


def void_order(order_id: uuid.UUID, reason: str) -> Order:
    from django.utils import timezone

    with transaction.atomic():
        order = _locked(order_id)
        if order.status == OrderStatus.SETTLED:
            raise OrderNotOpen("Cannot void a settled order.")
        order.status = OrderStatus.VOID
        order.voided_at = timezone.now()
        order.void_reason = reason
        order.save(update_fields=["status", "voided_at", "void_reason", "updated_at"])
    record_audit("order.voided", entity_type="order", entity_id=order_id,
                 changes={"reason": reason})
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return order
