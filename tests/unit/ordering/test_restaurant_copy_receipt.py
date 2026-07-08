"""Unit tests for Restaurant Copy (Accounting & Auditing Archive) receipt."""
import pytest
import uuid
from decimal import Decimal

from contexts.ordering.domain.enums import (
    OrderStatus,
    OrderType,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
    PrintJobType,
)
from contexts.ordering.models import Invoice, Order, OrderItem, Payment
from contexts.ordering.services.printing import (
    create_order_print_jobs,
    get_archived_restaurant_copy,
)
from contexts.ordering.services.print_templates import CustomerReceiptTemplate
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def settled_order_and_invoice(db, active_tenant):
    set_current_tenant(active_tenant.id)
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-AUDIT-101",
        status=OrderStatus.SETTLED,
        type=OrderType.DINE_IN,
        customer_name="Audit Reviewer",
        customer_phone="9988776655",
        subtotal=Decimal("1000.00"),
        cgst=Decimal("25.00"),
        sgst=Decimal("25.00"),
        total=Decimal("1050.00"),
    )

    OrderItem.objects.create(
        tenant=active_tenant,
        order=order,
        product_id=uuid.uuid4(),
        name_snapshot="Tandoori Platter",
        qty=Decimal("1.000"),
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        status="active",
    )

    Payment.objects.create(
        tenant=active_tenant,
        order=order,
        kind=PaymentKind.PAYMENT,
        method=PaymentMethod.CARD,
        amount=Decimal("1050.00"),
        tendered=Decimal("1050.00"),
        change_due=Decimal("0.00"),
        reference="CARD-TXN-REF-9988",
        status=PaymentStatus.CAPTURED,
    )

    invoice = Invoice.objects.create(
        number="INV-AUDIT-101",
        order=order,
        location_id=order.location_id,
        series="INV",
        subtotal=order.subtotal,
        discount_amount=Decimal("0.00"),
        service_charge_amount=Decimal("0.00"),
        cgst=order.cgst,
        sgst=order.sgst,
        total=order.total,
        customer_name="Audit Reviewer",
    )

    yield order, invoice
    clear_current_tenant()


@pytest.mark.django_db
def test_render_restaurant_copy_contains_all_customer_fields_plus_10_audit_fields(
    active_tenant, settled_order_and_invoice
):
    """Verify Restaurant Copy contains Customer Receipt items PLUS all 10 accounting & audit fields."""
    order, invoice = settled_order_and_invoice

    tpl = CustomerReceiptTemplate(paper_width="80mm")
    receipt = tpl.render_text(invoice, copy_type="RESTAURANT COPY")

    # 1. Check Customer Receipt core items
    assert "[ LOGO:" in receipt
    assert "TAX INVOICE" in receipt
    assert "INV-AUDIT-101" in receipt # Invoice Number
    assert "Audit Reviewer" in receipt # Customer Name
    assert "Tandoori Platter" in receipt # Item Name
    assert "GRAND TOTAL" in receipt # Grand Total
    assert "1050.00" in receipt
    assert "CARD" in receipt # Payment Method

    # 2. Check all 10 Internal Accounting & Auditing Fields
    assert "ACCOUNTING & AUDIT RECORD" in receipt
    assert "Internal Order #" in receipt
    assert str(order.id)[:18] in receipt # 1. Internal Order Number
    assert "Internal Txn ID" in receipt
    assert "CARD-TXN-REF-9988" in receipt # 2. Internal Transaction ID
    assert "Branch Name" in receipt # 3. Branch Name
    assert "Terminal ID" in receipt # 4. Terminal ID
    assert "POS-TRM-01" in receipt
    assert "Cashier ID" in receipt # 5. Cashier ID
    assert "Shift Number" in receipt # 6. Shift Number
    assert "SHIFT-01" in receipt
    assert "Company Name" in receipt # 7. Company Name
    assert "Company ID" in receipt # 8. Company ID
    assert "Audit Ref" in receipt # 9. Internal Audit Reference
    assert f"AUD-{order.id.hex[:12].upper()}" in receipt
    assert "Print Timestamp" in receipt # 10. Print Timestamp

    # Check Audit Archive footer
    assert "ACCOUNTING & AUDIT ARCHIVE RECORD" in receipt
    assert "RETAIN FOR FINANCIAL COMPLIANCE" in receipt


@pytest.mark.django_db
def test_restaurant_copy_archived_and_retrievable(active_tenant, settled_order_and_invoice):
    """Verify Restaurant Copy is archived in database and automatically generated on payment."""
    order, invoice = settled_order_and_invoice

    jobs = create_order_print_jobs(order, invoice, paper_width="80mm")

    restaurant_job = [j for j in jobs if j.job_type == PrintJobType.RESTAURANT_RECEIPT][0]
    assert "ACCOUNTING & AUDIT RECORD" in restaurant_job.content_text
    assert f"AUD-{order.id.hex[:12].upper()}" in restaurant_job.content_text

    # Verify retrieval via archive query helper
    archived = get_archived_restaurant_copy(invoice)
    assert archived is not None
    assert archived.id == restaurant_job.id


@pytest.mark.django_db
def test_to_escpos_restaurant_copy_commands(active_tenant, settled_order_and_invoice):
    """Verify native ESC/POS commands in Restaurant Copy payload."""
    order, invoice = settled_order_and_invoice

    tpl = CustomerReceiptTemplate(paper_width="80mm")
    escpos = tpl.render_escpos(invoice, copy_type="RESTAURANT COPY")
    assert escpos.startswith(b"\x1b\x40")
    assert escpos.endswith(b"\x1d\x56\x00")
