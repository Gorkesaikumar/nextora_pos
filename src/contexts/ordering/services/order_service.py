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
    order_type: str,
    table_id: uuid.UUID | None = None,
    is_interstate: bool = False,
    service_charge_rate: Decimal = Decimal("0"),
    created_by: uuid.UUID | None = None,
) -> Order:
    with transaction.atomic():
        number = sequences.next_number(None, "order")
        order = Order.objects.create(
            order_number=f"{number:04d}",
            table_id=table_id,
            type=order_type,
            is_interstate=is_interstate,
            service_charge_rate=service_charge_rate,
            created_by=created_by,
        )
    record_audit("order.created", entity_type="order", entity_id=order.id)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed", payload={"action": "created", "type": order.type}))
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

    sum_deltas = sum((m.price_delta for m in modifiers), Decimal("0"))
    modifiers_total = q(sum_deltas * Decimal(qty))
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
def add_combo(
    order_id: uuid.UUID,
    combo_offer,
    selections: list[dict],
) -> "ordering.models.OrderCombo":
    """
    selections = [
        {
            "product": Product,
            "variant": ProductVariant (optional),
            "modifiers": [Modifier] (optional),
            "qty": Decimal,
            "notes": str
        }
    ]
    """
    from contexts.ordering.models import OrderCombo
    from contexts.catalog.domain.enums import ComboOfferType

    order = _locked(order_id)
    if order.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))

    combo_record = OrderCombo.objects.create(
        order=order,
        combo_offer_id=combo_offer.id,
        name_snapshot=combo_offer.name,
        price=Decimal("0.00"),
        savings=Decimal("0.00")
    )

    # 1. Calculate raw total base price of all constituent items
    raw_total = Decimal("0.00")
    items_to_create = []

    for sel in selections:
        product = sel["product"]
        variant = sel.get("variant")
        modifiers = sel.get("modifiers") or []
        qty = Decimal(sel.get("qty", "1"))
        
        unit_price = product.base_price + (variant.price_delta if variant else Decimal("0"))
        mod_deltas = sum((m.price_delta for m in modifiers), Decimal("0"))
        
        line_raw_total = q((unit_price + mod_deltas) * qty)
        raw_total += line_raw_total
        
        items_to_create.append({
            "product": product,
            "variant": variant,
            "modifiers": modifiers,
            "qty": qty,
            "notes": sel.get("notes", ""),
            "unit_price": unit_price,
            "mod_deltas": mod_deltas,
            "raw_total": line_raw_total
        })

    # 2. Determine target combo price and total savings
    if combo_offer.offer_type == ComboOfferType.FIXED_PRICE:
        target_price = combo_offer.discount_value
    elif combo_offer.offer_type == ComboOfferType.PERCENTAGE:
        target_price = q(raw_total * (Decimal("100") - combo_offer.discount_value) / Decimal("100"))
    elif combo_offer.offer_type == ComboOfferType.FLAT_DISCOUNT:
        target_price = q(max(Decimal("0"), raw_total - combo_offer.discount_value))
    else:
        target_price = raw_total

    # Surcharges (from upgrades) can be added to target_price here if needed.
    # For now, we assume the combo fixed price handles everything or is adjusted prior.
    
    savings = q(max(Decimal("0"), raw_total - target_price))
    combo_record.price = target_price
    combo_record.savings = savings
    combo_record.save(update_fields=["price", "savings"])

    # 3. Create items with proportional line_discount
    allocated = Decimal("0.00")
    count = len(items_to_create)

    for index, data in enumerate(items_to_create):
        if raw_total > 0 and savings > 0:
            if index < count - 1:
                alloc = q(savings * data["raw_total"] / raw_total)
                allocated += alloc
            else:
                alloc = q(savings - allocated)
        else:
            alloc = Decimal("0.00")
            
        tax_rate = data["product"].tax_class.gst_rate if data["product"].tax_class else Decimal("0")
        cess_rate = data["product"].tax_class.cess_rate if data["product"].tax_class else Decimal("0")
        _, station = resolve_routing(data["product"])
        name = data["product"].name + (f" ({data['variant'].name})" if data["variant"] else "")
        
        modifiers_total = q(data["mod_deltas"] * data["qty"])
        
        item = OrderItem(
            order=order, product_id=data["product"].id,
            variant_id=data["variant"].id if data["variant"] else None,
            name_snapshot=name, qty=data["qty"], unit_price=data["unit_price"],
            modifiers_total=modifiers_total, tax_rate=tax_rate, cess_rate=cess_rate,
            hsn_code=getattr(data["product"], "hsn_code", ""),
            kitchen_station_id=station.id if station else None,
            notes=data["notes"],
            combo=combo_record,
            line_discount=alloc,
        )
        _refresh_item_totals(item)
        item.save()

        for modifier in data["modifiers"]:
            OrderItemModifier.objects.create(
                item=item, modifier_id=modifier.id,
                name_snapshot=modifier.name, price_delta=modifier.price_delta,
            )

    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return combo_record


@transaction.atomic
def remove_combo(order_id: uuid.UUID, combo_id: uuid.UUID) -> None:
    order = _locked(order_id)
    if order.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))
    
    from contexts.ordering.models import OrderCombo
    combo_record = OrderCombo.objects.get(id=combo_id, order=order)
    
    # Void all items in the combo
    order.items.filter(combo=combo_record, status=ItemStatus.ACTIVE).update(
        status=ItemStatus.VOID
    )
    
    # Actually delete the OrderCombo since it's transient
    combo_record.delete()

    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))


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
        sum_deltas = sum((m.price_delta for m in item.modifiers.all()), Decimal("0"))
        item.modifiers_total = q(sum_deltas * item.qty)
        _refresh_item_totals(item)
        item.save()
    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return item


@transaction.atomic
def update_item_modifiers(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    modifiers=None,
    notes: str = "",
) -> OrderItem:
    """Update modifiers and notes for an existing item in the cart and recalculate totals."""
    order = _locked(order_id)
    if order.status != OrderStatus.OPEN:
        raise OrderNotOpen(str(order_id))
    item = order.items.get(id=item_id, status=ItemStatus.ACTIVE)

    modifiers = modifiers or []
    item.modifiers.all().delete()

    for modifier in modifiers:
        OrderItemModifier.objects.create(
            item=item, modifier_id=modifier.id,
            name_snapshot=modifier.name, price_delta=modifier.price_delta,
        )

    sum_deltas = sum((m.price_delta for m in modifiers), Decimal("0"))
    item.modifiers_total = q(sum_deltas * item.qty)
    item.notes = notes
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
        order_number=f"{sequences.next_number(None, 'order'):04d}",
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
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed", payload={"action": "voided", "type": order.type, "total": float(order.total)}))
    return order
