"""Settlement + tax-invoice issuance.

Idempotent (one invoice per order) and concurrency-safe (order row locked,
number issued under a counter row lock). The invoice freezes the order's totals
at issue time so later edits cannot mutate a legal document.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from contexts.audit.services import record_audit
from contexts.ordering.domain.enums import InvoiceStatus, OrderStatus
from contexts.ordering.domain.finance import financial_year
from contexts.ordering.exceptions import (
    InvoiceNumberingError,
    OrderNotOpen,
    OutstandingDue,
)
from contexts.ordering.models import Invoice, Order
from contexts.ordering.services import sequences
from contexts.ordering.realtime import broadcast_tenant_event

# Invoice numbers are unique per (tenant, number) and the number string does not
# encode location, so the sequence is tenant-wide (location_id=None) rather than
# per-branch. The retry cap absorbs any historical counter drift (e.g. legacy
# per-location counter rows that left the sequence behind the issued numbers).
_MAX_NUMBER_ATTEMPTS = 50


def settle_and_invoice(
    order_id: uuid.UUID,
    *,
    series: str = "INV",
    now: datetime | None = None,
    on: date | None = None,
) -> Invoice:
    now = now or timezone.now()
    on = on or timezone.localdate()

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)

        # Idempotent: already invoiced -> return existing.
        existing = Invoice.objects.filter(order=order).first()
        if existing is not None:
            return existing

        if order.status == OrderStatus.VOID:
            raise OrderNotOpen("Cannot invoice a void order.")
        if order.due_amount > Decimal("0"):
            raise OutstandingDue(f"Due {order.due_amount} remaining.")

        invoice, number = _create_invoice_with_number(order, series=series, now=now, on=on)

        order.status = OrderStatus.SETTLED
        order.settled_at = now
        order.save(update_fields=["status", "settled_at", "updated_at"])

    record_audit("invoice.issued", entity_type="invoice", entity_id=invoice.id,
                 changes={"number": number, "total": str(order.total)})
    from shared.tenancy.context import get_current_tenant
    tid = get_current_tenant()
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed", tenant_id=tid))
    return invoice


def _create_invoice_with_number(
    order: Order, *, series: str, now: datetime, on: date
) -> tuple[Invoice, str]:
    """Allocate a free invoice number and create the invoice.

    Runs inside the caller's atomic block. Each attempt advances the tenant-wide
    daily counter; the INSERT is wrapped in its own savepoint so a duplicate
    number (counter drift) is caught without poisoning the outer transaction,
    then retried with the next number until one is free.
    """
    fields = dict(
        order=order, location_id=order.location_id, series=series,
        financial_year=financial_year(on),
        subtotal=order.subtotal, discount_amount=order.discount_amount,
        service_charge_amount=order.service_charge_amount,
        taxable_amount=order.taxable_amount,
        cgst=order.cgst, sgst=order.sgst, igst=order.igst, cess=order.cess,
        tax_amount=order.tax_amount, round_off=order.round_off,
        total=order.total, customer_name=order.customer_name,
        customer_phone=order.customer_phone, issued_at=now,
    )
    for _ in range(_MAX_NUMBER_ATTEMPTS):
        seq = sequences.next_number(None, "invoice", series=series, on=on)
        number = f"{series}{on:%y%m%d}-{seq:04d}"
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(number=number, **fields)
            return invoice, number
        except IntegrityError:
            continue
    raise InvoiceNumberingError(
        f"No free invoice number for {series}{on:%y%m%d} after "
        f"{_MAX_NUMBER_ATTEMPTS} attempts."
    )


def void_invoice(invoice_id: uuid.UUID, reason: str) -> Invoice:
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        invoice.status = InvoiceStatus.VOID
        invoice.voided_at = timezone.now()
        invoice.void_reason = reason
        invoice.save(update_fields=["status", "voided_at", "void_reason", "updated_at"])
    record_audit("invoice.voided", entity_type="invoice", entity_id=invoice_id,
                 changes={"reason": reason})
    return invoice
