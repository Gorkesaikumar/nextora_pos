import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from shared.tenancy.context import get_current_tenant, bypass_tenant
from contexts.audit.services import record_audit
from contexts.ordering.models import Order, OrderStatus, Refund, RefundStatus, RefundType, Payment, Invoice
from contexts.ordering.domain.enums import PaymentKind, PaymentMethod, PaymentStatus, InvoiceStatus
from contexts.ordering.exceptions import OrderNotOpen
from contexts.ordering.realtime import broadcast_tenant_event


@transaction.atomic
def initiate_refund(
    order_id: uuid.UUID,
    amount: Decimal,
    reason: str,
    refund_type: str = RefundType.FULL,
    payment_method: str | None = None,
    restock_inventory: bool = True,
    requested_by: uuid.UUID | None = None
) -> Refund:
    """
    Initiates a financial refund for an order/invoice.
    """
    tenant = get_current_tenant()
    
    if tenant:
        order = Order.objects.select_for_update().get(id=order_id, tenant=tenant)
    else:
        with bypass_tenant():
            order = Order.objects.select_for_update().get(id=order_id)
            tenant = order.tenant
    
    if order.status not in [OrderStatus.SETTLED, OrderStatus.VOID]:
        raise ValueError("Cannot refund an order that has not been settled.")
        
    # Calculate already refunded amount from existing completed refunds
    already_refunded = sum(
        r.amount for r in order.refunds.filter(status=RefundStatus.COMPLETED)
    )
    
    amount_dec = Decimal(str(amount))
    if amount_dec <= Decimal("0"):
        raise ValueError("Refund amount must be greater than zero.")
        
    if already_refunded + amount_dec > order.total + Decimal("0.01"):
        raise ValueError(
            f"Total refund amount (₹{already_refunded + amount_dec:.2f}) cannot exceed order total (₹{order.total:.2f})."
        )
        
    # Determine payment method for refund reversal
    if not payment_method:
        orig_pm = order.payments.filter(kind=PaymentKind.PAYMENT, status=PaymentStatus.CAPTURED).first()
        payment_method = orig_pm.method if orig_pm else PaymentMethod.CASH

    refund = Refund.objects.create(
        tenant=tenant,
        order=order,
        amount=amount_dec,
        reason=reason,
        refund_type=refund_type,
        status=RefundStatus.COMPLETED,
        requested_by=requested_by,
        approved_by=requested_by
    )
    
    # Create Payment reversal record (kind=REFUND) so reports and dashboards track refunds accurately
    Payment.objects.create(
        tenant=tenant,
        order=order,
        kind=PaymentKind.REFUND,
        method=payment_method,
        amount=amount_dec,
        change_due=Decimal("0.00"),
        status=PaymentStatus.CAPTURED,
        refund_reason=reason,
        created_by=requested_by
    )
    
    is_full_refund = (already_refunded + amount_dec >= order.total - Decimal("0.01")) or (refund_type == RefundType.FULL)
    
    # Update order and invoice status if fully refunded
    if is_full_refund:
        order.status = OrderStatus.VOID
        order.save(update_fields=["status", "updated_at"])
        
        # Void associated tax invoice
        inv = Invoice.objects.filter(order=order).first()
        if inv and inv.status != InvoiceStatus.VOID:
            inv.status = InvoiceStatus.VOID
            inv.voided_at = timezone.now()
            inv.void_reason = reason
            inv.save(update_fields=["status", "voided_at", "void_reason", "updated_at"])
            
    # Restock inventory if requested
    if restock_inventory:
        from contexts.inventory.models import InventoryItem
        from contexts.inventory.domain.enums import StockMovementType
        from contexts.inventory.services.movement_service import apply_stock_movement
        
        for item in order.items.filter(status="active"):
            inv_item = InventoryItem.objects.filter(product_id=item.product_id).first()
            if inv_item:
                # For partial refund, calculate restock ratio if needed, or restock full qty on full refund
                qty_to_restock = item.qty if is_full_refund else (item.qty * (amount_dec / order.total)).quantize(Decimal("0.01"))
                if qty_to_restock > Decimal("0"):
                    apply_stock_movement(
                        inventory_item_id=inv_item.id,
                        movement_type=StockMovementType.RETURN_CUSTOMER,
                        quantity=qty_to_restock,
                        reference_type="REFUND",
                        reference_id=refund.id,
                        reference_number=order.order_number,
                        notes=f"Customer Refund #{refund.id}: {reason}",
                        performed_by_id=requested_by,
                        allow_negative=True
                    )
    
    # Record audit log
    record_audit(
        action="refund.processed",
        entity_type="refund",
        entity_id=str(refund.id),
        changes={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "amount": str(amount_dec),
            "reason": reason,
            "type": refund_type,
            "method": payment_method,
            "restock": restock_inventory,
        }
    )
    
    # Real-time event broadcast
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    transaction.on_commit(lambda: broadcast_tenant_event("payment_captured"))
    
    return refund

