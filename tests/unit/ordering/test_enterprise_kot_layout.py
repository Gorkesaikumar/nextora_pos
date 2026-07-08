"""Unit tests for Enterprise Kitchen Order Ticket (KOT) layout and formatting."""
import pytest
import uuid
from decimal import Decimal

from contexts.ordering.domain.enums import (
    KOTStatus,
    OrderStatus,
    OrderType,
)
from contexts.ordering.models import KOT, KOTItem, Order, OrderItem, OrderItemModifier
from contexts.ordering.services.print_templates import KOTTemplate
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def enterprise_kot_with_modifiers(db, active_tenant):
    set_current_tenant(active_tenant.id)
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-2026-888",
        status=OrderStatus.OPEN,
        type=OrderType.DINE_IN,
        customer_name="Chef Gourmet Tester",
        subtotal=Decimal("1500.00"),
        discount_amount=Decimal("100.00"),
        cgst=Decimal("35.00"),
        sgst=Decimal("35.00"),
        total=Decimal("1470.00"),
    )

    order_item = OrderItem.objects.create(
        tenant=active_tenant,
        order=order,
        product_id=uuid.uuid4(),
        name_snapshot="Paneer Tikka Masala",
        qty=Decimal("2.00"),
        unit_price=Decimal("750.00"),
        line_total=Decimal("1500.00"),
        modifiers_total=Decimal("50.00"),
        notes="Extra Spicy & Less Oil",
        status="active",
    )

    OrderItemModifier.objects.create(
        tenant=active_tenant,
        item=order_item,
        modifier_id=uuid.uuid4(),
        name_snapshot="Extra Cheese Add-on",
        price_delta=Decimal("50.00"),
        qty=Decimal("1.00"),
    )

    kot = KOT.objects.create(
        tenant=active_tenant,
        order=order,
        location_id=order.location_id,
        number=42,
        status=KOTStatus.NEW,
    )

    KOTItem.objects.create(
        tenant=active_tenant,
        kot=kot,
        order_item=order_item,
        name_snapshot="Paneer Tikka Masala",
        qty=Decimal("2.00"),
        notes="Extra Spicy & Less Oil",
    )

    yield kot
    clear_current_tenant()


@pytest.mark.django_db
def test_render_kot_text_contains_all_kitchen_info_and_excludes_financials(active_tenant, enterprise_kot_with_modifiers):
    """Verify KOT includes all kitchen items/modifiers and excludes all prices, taxes, and totals."""
    kot = enterprise_kot_with_modifiers

    tpl = KOTTemplate(paper_width="80mm")
    kot_text = tpl.render_text(kot)

    # 1. Check all Kitchen-related operational info
    assert "KITCHEN ORDER TICKET" in kot_text
    assert "#42" in kot_text  # KOT Number
    assert "ORD-2026-888" in kot_text  # Order Number
    assert "Dine In" in kot_text  # Order Type
    assert "Chef Gourmet Tester" in kot_text  # Customer Name
    assert "[ 2 ]  PANEER TIKKA MASALA" in kot_text  # Quantity and Item Name
    assert "+ Extra Cheese Add-on" in kot_text  # Modifiers & Add-ons
    assert "*** NOTE: Extra Spicy & Less Oil ***" in kot_text  # Special Instructions / Kitchen Notes

    # 2. Check strict EXCLUSION of all financial information
    assert "1500.00" not in kot_text  # No unit price / subtotal
    assert "750.00" not in kot_text  # No item unit price
    assert "50.00" not in kot_text  # No modifier price
    assert "1470.00" not in kot_text  # No Grand Total
    assert "CGST" not in kot_text
    assert "SGST" not in kot_text
    assert "Discount" not in kot_text
    assert "Payment" not in kot_text


@pytest.mark.django_db
def test_to_escpos_kot_commands(active_tenant, enterprise_kot_with_modifiers):
    """Verify ESC/POS hardware formatting includes double height/width commands for fast kitchen readability."""
    kot = enterprise_kot_with_modifiers

    tpl = KOTTemplate(paper_width="80mm")
    escpos = tpl.render_escpos(kot)

    # Must start with ESC @ (printer init)
    assert escpos.startswith(b"\x1b\x40")
    # Must contain GS ! 0x11 (double height + width) for title readability
    assert b"\x1d\x21\x11" in escpos
    # Must end with full cut
    assert escpos.endswith(b"\x1d\x56\x00")
