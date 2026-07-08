"""Enterprise Checkout & Settlement Service.

Refactors the Complete Payment workflow into a single atomic database transaction
executing the strict 13-step lifecycle:
1. Validate Cart
2. Validate Inventory
3. Validate Payment
4. Create Sale
5. Create Invoice
6. Generate Invoice Number
7. Generate KOT Number
8. Deduct Inventory
9. Record Payment
10. Save Audit Log
11. Commit Transaction
12. Print Receipts (strictly after successful transaction commit)
13. Clear Cart (session clear & table release handled cleanly post-commit)

Prevents duplicate invoices and duplicate payments via database-level idempotency checks.
If any database step fails, the entire transaction rolls back.
"""
import uuid
from decimal import Decimal

from django.db import transaction

from contexts.audit.services import record_audit
from contexts.ordering.domain.enums import OrderStatus, PaymentMethod
from contexts.ordering.models import Order, Invoice
from contexts.ordering.services import (
    invoice_service,
    kot_service,
    payment_service,
)
from contexts.ordering.services.printing import (
    PrintJob,
    create_order_print_jobs,
    dispatch_print_jobs_on_commit,
)


@transaction.atomic
def complete_checkout_transaction(
    order_id: uuid.UUID,
    method: str,
    tendered: Decimal | None = None,
    performed_by_id: uuid.UUID | None = None,
    paper_width: str = "80mm",
) -> tuple[Order, Invoice, list[PrintJob]]:
    """Execute complete checkout payment and settlement in a single atomic database transaction.

    If any database step fails, rolls back the entire transaction.
    Printing is dispatched via transaction.on_commit only after a successful commit.
    """
    # Acquire exclusive row lock on the order
    order = Order.objects.select_for_update().get(id=order_id)

    # --- Idempotency Check: Prevent duplicate invoices and duplicate payments ---
    if order.status == OrderStatus.SETTLED:
        existing_invoice = Invoice.objects.filter(order=order).first()
        existing_jobs = list(order.print_jobs.all())
        return order, existing_invoice, existing_jobs

    # 1. Validate Cart
    active_items = list(order.items.filter(status="active"))
    if not active_items:
        raise ValueError("Cart is empty. Cannot complete payment for an empty order.")
    if order.total < Decimal("0"):
        raise ValueError("Order total cannot be negative.")

    # 2. Validate Inventory
    from contexts.inventory.models import InventoryItem
    inventory_items_map = {}
    for item in active_items:
        inv_item = InventoryItem.objects.filter(product_id=item.product_id).first()
        if inv_item and not inv_item.is_active:
            raise ValueError(f"Inventory item for product '{item.name_snapshot}' is inactive.")
        if inv_item:
            inventory_items_map[item.id] = inv_item

    # 3. Validate Payment
    if not method:
        raise ValueError("Payment method is required.")
    if tendered is None:
        tendered = order.total
    tendered_dec = Decimal(str(tendered))
    if method == PaymentMethod.CASH and tendered_dec < order.total:
        raise ValueError(f"Tendered amount ({tendered_dec}) is less than order total ({order.total}).")

    # 9. Record Payment FIRST — this calls _recompute(), setting order.due_amount = 0.
    # The invoice service checks due_amount > 0, so payment must exist before invoicing.
    payment_service.add_payment(
        order_id=order.id,
        amount=order.total,
        method=method,
        tendered=tendered_dec,
        created_by=performed_by_id,
    )

    # Reload order so in-memory due_amount reflects the payment just recorded.
    order.refresh_from_db()

    # 4. Create Sale + 5. Create Invoice + 6. Generate Invoice Number
    # settle_and_invoice checks order.due_amount == 0 (now satisfied after payment above),
    # creates the Invoice, generates gapless Invoice Number, and sets order.status = SETTLED.
    invoice = invoice_service.settle_and_invoice(order.id)

    # 7. Generate KOT Number
    kots = kot_service.generate_kots(order.id)

    # 8. Deduct Inventory
    from contexts.inventory.domain.enums import StockMovementType
    from contexts.inventory.services.movement_service import apply_stock_movement

    for item in active_items:
        inv_item = inventory_items_map.get(item.id)
        if inv_item:
            apply_stock_movement(
                inventory_item_id=inv_item.id,
                movement_type=StockMovementType.SALE,
                quantity=-item.qty,
                reference_type="ORDER",
                reference_id=order.id,
                reference_number=order.order_number,
                notes=f"POS Sale #{order.order_number}",
                performed_by_id=performed_by_id,
                allow_negative=True,
            )
        for mod in item.modifiers.all():
            from contexts.catalog.models.modifier import Modifier
            modifier_obj = Modifier.objects.filter(id=mod.modifier_id).first()
            if modifier_obj and modifier_obj.inventory_item_id:
                consume_qty = item.qty * modifier_obj.quantity_consumed
                apply_stock_movement(
                    inventory_item_id=modifier_obj.inventory_item_id,
                    movement_type=StockMovementType.SALE,
                    quantity=-consume_qty,
                    reference_type="ORDER",
                    reference_id=order.id,
                    reference_number=order.order_number,
                    notes=f"POS Sale #{order.order_number} (Modifier: {modifier_obj.name})",
                    performed_by_id=performed_by_id,
                    allow_negative=True,
                )

    # 10. Save Audit Log
    record_audit(
        "checkout.completed",
        entity_type="order",
        entity_id=order.id,
        changes={
            "invoice_number": invoice.number,
            "total": str(order.total),
            "payment_method": method,
            "cashier_id": str(performed_by_id) if performed_by_id else None,
        },
    )

    # Prepare PrintJobs inside the transaction so they are committed atomically
    print_jobs = create_order_print_jobs(
        order=order,
        invoice=invoice,
        kots=kots,
        paper_width=paper_width,
    )

    # 11. Commit Transaction (automatic upon normal exit of transaction.atomic)

    # 12. Print Receipts (strictly after successful database commit)
    transaction.on_commit(lambda: dispatch_print_jobs_on_commit(print_jobs))

    return order, invoice, print_jobs
