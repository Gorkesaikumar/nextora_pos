"""End-to-end POS engine tests: items, split/merge, payments, refunds,
invoicing (idempotent + daily reset), KOT and printing."""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from contexts.catalog.models import Category, KitchenStation, Product, TaxClass
from contexts.ordering.domain.enums import OrderStatus
from contexts.ordering.exceptions import OutstandingDue, OverRefund
from contexts.ordering.models import KOT, Invoice, Order, Payment
from contexts.ordering.services import (
    invoice_service,
    kot_service,
    order_service,
    payment_service,
    printing,
)

pytestmark = pytest.mark.django_db

LOCATION = uuid.uuid4()


def _product(name="Burger", price="100", gst=18, station=None):
    suffix = uuid.uuid4().hex[:6]
    category = Category.objects.create(
        name=f"{name}-{suffix}-cat",
        slug=f"{name.lower()}-{suffix}-cat",
        station_id=station.id if station else None,
    )
    tax = TaxClass.objects.create(name=f"GST{gst}-{name}-{suffix}", gst_rate=Decimal(gst))
    return Product.objects.create(
        category=category, tax_class=tax, name=name, sku=f"{name}-{suffix}",
        base_price=Decimal(price),
    )


def _open_order():
    return order_service.create_order(location_id=LOCATION, order_type="dine_in")


def _paid_order(total_check="118.00"):
    order = _open_order()
    order_service.add_item(order.id, _product())
    payment_service.add_payment(order.id, Decimal("118"), "cash", tendered=Decimal("120"))
    refreshed = Order.objects.get(id=order.id)
    assert refreshed.total == Decimal(total_check)
    return refreshed


# --- Items / totals --------------------------------------------------------
def test_add_item_recalculates_bill(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product(price="100", gst=18))
    order = Order.objects.get(id=order.id)
    assert order.subtotal == Decimal("100.00")
    assert order.tax_amount == Decimal("18.00")
    assert order.total == Decimal("118.00")
    assert order.due_amount == Decimal("118.00")


def test_discount_applies(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product(price="100", gst=18))
    order_service.apply_discount(order.id, "flat", Decimal("10"))
    order = Order.objects.get(id=order.id)
    assert order.discount_amount == Decimal("10.00")
    assert order.total == Decimal("106.00")  # 90 + 16.20 = 106.20 -> 106


# --- Split / merge ---------------------------------------------------------
def test_split_moves_items_to_new_bill(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product(name="A", price="100"))
    item_b = order_service.add_item(order.id, _product(name="B", price="200"))

    new_order = order_service.split_order(order.id, [{"item_id": item_b.id}])

    source = Order.objects.get(id=order.id)
    target = Order.objects.get(id=new_order.id)
    assert source.subtotal == Decimal("100.00")
    assert target.subtotal == Decimal("200.00")
    assert target.split_from_id == source.id


def test_partial_quantity_split(active_tenant):
    order = _open_order()
    item = order_service.add_item(order.id, _product(price="100"), qty=Decimal("3"))
    new_order = order_service.split_order(
        order.id, [{"item_id": item.id, "qty": Decimal("1")}]
    )
    assert Order.objects.get(id=order.id).subtotal == Decimal("200.00")   # 2 left
    assert Order.objects.get(id=new_order.id).subtotal == Decimal("100.00")  # 1 moved


def test_merge_combines_bills(active_tenant):
    a = _open_order()
    b = _open_order()
    order_service.add_item(a.id, _product(name="A", price="100"))
    order_service.add_item(b.id, _product(name="B", price="50"))

    order_service.merge_orders(a.id, [b.id])

    assert Order.objects.get(id=a.id).subtotal == Decimal("150.00")
    source_b = Order.objects.get(id=b.id)
    assert source_b.status == OrderStatus.VOID
    assert source_b.merged_into_id == a.id


# --- Payments --------------------------------------------------------------
def test_partial_and_multiple_payment_methods(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product())  # total 118
    payment_service.add_payment(order.id, Decimal("50"), "cash")
    assert Order.objects.get(id=order.id).due_amount == Decimal("68.00")

    payment_service.add_payment(order.id, Decimal("68"), "upi", reference="upi-1")
    order = Order.objects.get(id=order.id)
    assert order.paid_amount == Decimal("118.00")
    assert order.due_amount == Decimal("0.00")
    assert order.payments.count() == 2


def test_payment_is_idempotent(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product())
    payment_service.add_payment(order.id, Decimal("50"), "card", idempotency_key="k1")
    payment_service.add_payment(order.id, Decimal("50"), "card", idempotency_key="k1")
    order = Order.objects.get(id=order.id)
    assert order.payments.count() == 1
    assert order.paid_amount == Decimal("50.00")


def test_payment_idempotency_survives_unique_clash(active_tenant):
    """If a row with the key already exists (e.g. a concurrent winner), the
    call returns it instead of raising IntegrityError."""
    order = _open_order()
    order_service.add_item(order.id, _product())
    first = payment_service.add_payment(order.id, Decimal("50"), "card", idempotency_key="dup")
    # Simulate the "already inserted by a concurrent request" path.
    second = payment_service.add_payment(order.id, Decimal("50"), "card", idempotency_key="dup")
    assert first.id == second.id
    assert Payment.objects.filter(order=order).count() == 1


def test_cash_change_due(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product())
    payment = payment_service.add_payment(
        order.id, Decimal("118"), "cash", tendered=Decimal("200")
    )
    assert payment.change_due == Decimal("82.00")


def test_refund_reduces_paid(active_tenant):
    order = _paid_order()
    payment_service.refund_payment(order.id, Decimal("18"), "upi", reason="item issue")
    order = Order.objects.get(id=order.id)
    assert order.paid_amount == Decimal("100.00")
    assert order.due_amount == Decimal("18.00")


def test_refund_cannot_exceed_paid(active_tenant):
    order = _paid_order()
    with pytest.raises(OverRefund):
        payment_service.refund_payment(order.id, Decimal("500"), "upi")


# --- Void ------------------------------------------------------------------
def test_void_order(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product())
    order_service.void_order(order.id, "customer left")
    assert Order.objects.get(id=order.id).status == OrderStatus.VOID


def test_void_item_recalculates(active_tenant):
    order = _open_order()
    a = order_service.add_item(order.id, _product(name="A", price="100"))
    order_service.add_item(order.id, _product(name="B", price="200"))
    order_service.void_item(order.id, a.id)
    assert Order.objects.get(id=order.id).subtotal == Decimal("200.00")


# --- Invoicing -------------------------------------------------------------
def test_settle_requires_zero_due(active_tenant):
    order = _open_order()
    order_service.add_item(order.id, _product())
    with pytest.raises(OutstandingDue):
        invoice_service.settle_and_invoice(order.id)


def test_settle_creates_invoice_and_marks_settled(active_tenant):
    order = _paid_order()
    invoice = invoice_service.settle_and_invoice(order.id, on=date(2026, 6, 27))
    assert invoice.number.endswith("260627-0001")
    assert invoice.total == Decimal("118.00")
    assert Order.objects.get(id=order.id).status == OrderStatus.SETTLED


def test_invoice_is_idempotent(active_tenant):
    order = _paid_order()
    inv1 = invoice_service.settle_and_invoice(order.id)
    inv2 = invoice_service.settle_and_invoice(order.id)
    assert inv1.id == inv2.id
    assert Invoice.objects.filter(order=order).count() == 1


def test_invoice_numbers_reset_daily(active_tenant):
    inv1 = invoice_service.settle_and_invoice(_paid_order().id, on=date(2026, 6, 27))
    inv2 = invoice_service.settle_and_invoice(_paid_order().id, on=date(2026, 6, 27))
    inv3 = invoice_service.settle_and_invoice(_paid_order().id, on=date(2026, 6, 28))

    assert inv1.number.endswith("260627-0001")
    assert inv2.number.endswith("260627-0002")
    assert inv3.number.endswith("260628-0001")  # reset for the new day


# --- KOT -------------------------------------------------------------------
def test_kot_groups_by_station_and_numbers(active_tenant):
    grill = KitchenStation.objects.create(code="GRILL", name="Grill")
    bar = KitchenStation.objects.create(code="BAR", name="Bar")
    order = _open_order()
    order_service.add_item(order.id, _product(name="Steak", station=grill))
    order_service.add_item(order.id, _product(name="Mojito", station=bar))

    kots = kot_service.generate_kots(order.id)
    assert len(kots) == 2
    # Re-running creates none (items already routed).
    assert kot_service.generate_kots(order.id) == []
    assert KOT.objects.filter(order=order).count() == 2


# --- Printing --------------------------------------------------------------
def test_render_invoice_and_kot_text(active_tenant):
    grill = KitchenStation.objects.create(code="GRILL", name="Grill")
    order = _open_order()
    order_service.add_item(order.id, _product(name="Steak", station=grill))
    payment_service.add_payment(order.id, Decimal("118"), "cash")
    kots = kot_service.generate_kots(order.id)
    invoice = invoice_service.settle_and_invoice(order.id)

    inv_text = printing.render_invoice_text(invoice)
    assert "TAX INVOICE" in inv_text
    assert invoice.number in inv_text
    assert "TOTAL" in inv_text

    kot_text = printing.render_kot_text(kots[0])
    assert "KITCHEN ORDER TICKET" in kot_text
    assert printing.to_escpos(kot_text).endswith(b"\x1d\x56\x00")
