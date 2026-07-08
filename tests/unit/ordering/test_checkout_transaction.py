"""Unit tests for atomic complete_checkout_transaction workflow."""
import uuid
from decimal import Decimal
import pytest
from django.db import transaction

from contexts.ordering.domain.enums import OrderStatus, OrderType, PaymentMethod
from contexts.ordering.models import Invoice, Order, OrderItem, Payment
from contexts.ordering.services.checkout_service import complete_checkout_transaction
from contexts.ordering.services.printing import PrintJob
from contexts.inventory.models import InventoryItem, Warehouse, StockMovement
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def checkout_test_data(db, active_tenant):
    set_current_tenant(active_tenant.id)
    warehouse = Warehouse.objects.create(
        tenant=active_tenant,
        code="MAIN",
        name="Main Kitchen Warehouse",
    )

    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-TXN-501",
        status=OrderStatus.OPEN,
        type=OrderType.DINE_IN,
        customer_name="Complete Payment Tester",
        subtotal=Decimal("500.00"),
        total=Decimal("500.00"),
    )

    product_id = uuid.uuid4()
    order_item = OrderItem.objects.create(
        tenant=active_tenant,
        order=order,
        product_id=product_id,
        name_snapshot="Masala Dosa",
        qty=Decimal("2.00"),
        unit_price=Decimal("250.00"),
        line_total=Decimal("500.00"),
        status="active",
    )

    inv_item = InventoryItem.objects.create(
        tenant=active_tenant,
        product_id=product_id,
        product_sku="DOSA-001",
        product_name="Masala Dosa",
        warehouse=warehouse,
        quantity_on_hand=Decimal("50.000"),
        is_active=True,
    )

    yield order, inv_item
    clear_current_tenant()


@pytest.mark.django_db(transaction=True)
def test_complete_checkout_transaction_executes_all_steps_in_atomic_order(active_tenant, checkout_test_data):
    """Verify complete checkout transaction validates cart, deducts stock, creates sale/invoice/KOT, records payment, and schedules receipts."""
    order, inv_item = checkout_test_data

    order, invoice, print_jobs = complete_checkout_transaction(
        order_id=order.id,
        method=PaymentMethod.CASH,
        tendered=Decimal("500.00"),
    )

    # Verify Order is settled
    order.refresh_from_db()
    assert order.status == OrderStatus.SETTLED

    # Verify Invoice created
    assert invoice is not None
    assert invoice.number.startswith("INV")
    assert invoice.order == order

    # Verify Payment recorded
    payments = Payment.objects.filter(order=order)
    assert payments.count() == 1
    assert payments.first().amount == Decimal("500.00")

    # Verify Inventory deducted via apply_stock_movement (-2.000)
    inv_item.refresh_from_db()
    assert inv_item.quantity_on_hand == Decimal("48.000")

    movements = StockMovement.objects.filter(inventory_item=inv_item)
    assert movements.count() == 1
    assert movements.first().quantity == Decimal("-2.000")

    # Verify PrintJobs created for printing strictly post-commit
    assert len(print_jobs) == 3


@pytest.mark.django_db(transaction=True)
def test_complete_checkout_transaction_idempotent_no_duplicate_invoice_or_payment(active_tenant, checkout_test_data):
    """Verify calling complete_checkout_transaction multiple times does not create duplicate invoices, payments, or deductions."""
    order, inv_item = checkout_test_data

    # First call
    order1, invoice1, jobs1 = complete_checkout_transaction(
        order_id=order.id,
        method=PaymentMethod.CASH,
        tendered=Decimal("500.00"),
    )

    # Second call (idempotent replay)
    order2, invoice2, jobs2 = complete_checkout_transaction(
        order_id=order.id,
        method=PaymentMethod.CASH,
        tendered=Decimal("500.00"),
    )

    assert invoice1.id == invoice2.id
    assert Payment.objects.filter(order=order).count() == 1
    inv_item.refresh_from_db()
    assert inv_item.quantity_on_hand == Decimal("48.000")  # Only deducted once


@pytest.mark.django_db(transaction=True)
def test_complete_checkout_transaction_rollback_on_failure(active_tenant, checkout_test_data):
    """Verify that if any validation or database step fails, the transaction rolls back cleanly."""
    order, inv_item = checkout_test_data

    # Attempt checkout with invalid tendered amount (less than total)
    with pytest.raises(ValueError, match="Tendered amount"):
        complete_checkout_transaction(
            order_id=order.id,
            method=PaymentMethod.CASH,
            tendered=Decimal("100.00"),
        )

    # Verify complete rollback
    order.refresh_from_db()
    assert order.status == OrderStatus.OPEN
    assert not Invoice.objects.filter(order=order).exists()
    assert not Payment.objects.filter(order=order).exists()

    inv_item.refresh_from_db()
    assert inv_item.quantity_on_hand == Decimal("50.000")  # No stock deducted
    assert not StockMovement.objects.filter(inventory_item=inv_item).exists()
