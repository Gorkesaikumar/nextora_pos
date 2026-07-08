"""Unit tests for complete enterprise Customer Receipt layout (58mm & 80mm + ESC/POS)."""
import pytest
import uuid
from decimal import Decimal

from contexts.ordering.domain.enums import (
    OrderStatus,
    OrderType,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from contexts.ordering.models import Invoice, Order, OrderItem, Payment
from contexts.ordering.services.print_templates import CustomerReceiptTemplate
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def detailed_order_and_invoice(db, active_tenant):
    set_current_tenant(active_tenant.id)
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-2026-999",
        status=OrderStatus.SETTLED,
        type=OrderType.DINE_IN,
        customer_name="Praveen Kumar",
        customer_phone="9876543210",
        subtotal=Decimal("500.00"),
        discount_amount=Decimal("50.00"),
        service_charge_amount=Decimal("20.00"),
        cgst=Decimal("11.75"),
        sgst=Decimal("11.75"),
        total=Decimal("493.50"),
    )

    OrderItem.objects.create(
        tenant=active_tenant,
        order=order,
        product_id=uuid.uuid4(),
        name_snapshot="Paneer Butter Masala",
        qty=Decimal("2.000"),
        unit_price=Decimal("250.00"),
        line_total=Decimal("500.00"),
        status="active",
    )

    Payment.objects.create(
        tenant=active_tenant,
        order=order,
        kind=PaymentKind.PAYMENT,
        method=PaymentMethod.CASH,
        amount=Decimal("493.50"),
        tendered=Decimal("500.00"),
        change_due=Decimal("6.50"),
        status=PaymentStatus.CAPTURED,
    )

    invoice = Invoice.objects.create(
        number="INV-2026-999",
        order=order,
        location_id=order.location_id,
        series="INV",
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        service_charge_amount=order.service_charge_amount,
        cgst=order.cgst,
        sgst=order.sgst,
        total=order.total,
        customer_name="Praveen Kumar",
    )

    yield order, invoice
    clear_current_tenant()


@pytest.mark.django_db
def test_render_invoice_text_contains_all_required_fields_80mm(active_tenant, detailed_order_and_invoice):
    """Verify all 20 required fields are present in 80mm layout."""
    order, invoice = detailed_order_and_invoice

    tpl = CustomerReceiptTemplate(paper_width="80mm")
    receipt = tpl.render_text(invoice, copy_type="CUSTOMER COPY")

    # Verify key required items
    assert "[ LOGO:" in receipt
    assert "TAX INVOICE" in receipt
    assert "*** CUSTOMER COPY ***" in receipt
    assert "GSTIN:" in receipt
    assert "INV-2026-999" in receipt  # Invoice Number
    assert "Cashier" in receipt       # Cashier Name
    assert "Praveen Kumar" in receipt # Customer Name
    assert "Order Type" in receipt    # Order Type
    assert "Paneer Butter Masala" in receipt  # Item Name
    assert "Subtotal" in receipt
    assert "Discount" in receipt      # Discounts
    assert "-50.00" in receipt
    assert "CGST" in receipt          # Taxes
    assert "SGST" in receipt
    assert "GRAND TOTAL" in receipt   # Grand Total
    assert "493.50" in receipt
    assert "Payment Method" in receipt
    assert "CASH" in receipt
    assert "Amount Paid" in receipt   # Amount Paid (Tendered)
    assert "500.00" in receipt
    assert "Balance Returned" in receipt  # Balance Returned (Change)
    assert "6.50" in receipt
    assert "THANK YOU FOR YOUR VISIT!" in receipt  # Thank You message

    # Verify row width fits 48 columns (80mm)
    for line in receipt.splitlines():
        assert len(line) <= 48


@pytest.mark.django_db
def test_render_invoice_text_contains_all_required_fields_58mm(active_tenant, detailed_order_and_invoice):
    """Verify compact 58mm layout fits 32 columns and formats all fields cleanly."""
    order, invoice = detailed_order_and_invoice
    tpl = CustomerReceiptTemplate(paper_width="58mm")
    receipt = tpl.render_text(invoice, copy_type="CUSTOMER COPY")

    assert "INV-2026-999" in receipt
    assert "GRAND TOTAL" in receipt
    assert "THANK YOU FOR YOUR VISIT!" in receipt

    # Verify row width fits 32 columns (58mm)
    for line in receipt.splitlines():
        assert len(line) <= 32


@pytest.mark.django_db
def test_to_escpos_receipt_formatting(active_tenant, detailed_order_and_invoice):
    """Verify native ESC/POS hardware control codes are generated."""
    order, invoice = detailed_order_and_invoice
    tpl = CustomerReceiptTemplate(paper_width="80mm")
    escpos_bytes = tpl.render_escpos(invoice, copy_type="CUSTOMER COPY")

    assert escpos_bytes.startswith(b"\x1b\x40")     # ESC @ initialization
    assert b"\x1b\x45\x01" in escpos_bytes          # ESC E 1 bold ON
    assert b"\x1b\x45\x00" in escpos_bytes          # ESC E 0 bold OFF
    assert escpos_bytes.endswith(b"\x1d\x56\x00")   # GS V 0 full cut
