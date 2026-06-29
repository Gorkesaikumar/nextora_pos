"""Payments and refunds — partial, multi-method, idempotent, concurrency-safe."""
import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from contexts.audit.services import record_audit
from contexts.ordering.domain.enums import (
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from contexts.ordering.domain.finance import q
from contexts.ordering.exceptions import OverRefund
from contexts.ordering.models import Order, Payment
from contexts.ordering.realtime import broadcast_tenant_event


def _net_paid(order: Order) -> Decimal:
    captured = sum(
        (p.amount for p in order.payments.filter(
            kind=PaymentKind.PAYMENT, status=PaymentStatus.CAPTURED)),
        Decimal("0"),
    )
    refunded = sum(
        (p.amount for p in order.payments.filter(kind=PaymentKind.REFUND)),
        Decimal("0"),
    )
    return q(captured - refunded)


def _recompute(order: Order) -> None:
    order.paid_amount = _net_paid(order)
    order.due_amount = q(order.total - order.paid_amount)
    order.save(update_fields=["paid_amount", "due_amount", "updated_at"])


def add_payment(
    order_id: uuid.UUID,
    amount: Decimal,
    method: str,
    *,
    idempotency_key: str = "",
    reference: str = "",
    tendered: Decimal | None = None,
    created_by: uuid.UUID | None = None,
) -> Payment:
    amount = q(amount)
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)

        if idempotency_key:
            existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing  # idempotent replay

        change_due = Decimal("0.00")
        if method == PaymentMethod.CASH and tendered is not None:
            change_due = q(max(Decimal("0"), Decimal(tendered) - amount))

        try:
            with transaction.atomic():  # savepoint to survive a unique clash
                payment = Payment.objects.create(
                    order=order, kind=PaymentKind.PAYMENT, method=method,
                    amount=amount, tendered=tendered, change_due=change_due,
                    reference=reference, idempotency_key=idempotency_key,
                    captured_at=timezone.now(), created_by=created_by,
                )
        except IntegrityError:
            # Concurrent request with the same idempotency key won the insert.
            if idempotency_key:
                return Payment.objects.get(idempotency_key=idempotency_key)
            raise

        _recompute(order)
        record_audit("payment.captured", entity_type="order", entity_id=order_id,
                     changes={"amount": str(amount), "method": method})
        transaction.on_commit(lambda: broadcast_tenant_event("payment_captured"))
        transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return payment


def refund_payment(
    order_id: uuid.UUID,
    amount: Decimal,
    method: str,
    *,
    reason: str = "",
    idempotency_key: str = "",
    created_by: uuid.UUID | None = None,
) -> Payment:
    amount = q(amount)
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)

        if idempotency_key:
            existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing

        if amount > _net_paid(order):
            raise OverRefund(
                f"Refund {amount} exceeds net paid {_net_paid(order)}."
            )

        try:
            with transaction.atomic():
                refund = Payment.objects.create(
                    order=order, kind=PaymentKind.REFUND, method=method,
                    amount=amount, refund_reason=reason,
                    idempotency_key=idempotency_key,
                    captured_at=timezone.now(), created_by=created_by,
                )
        except IntegrityError:
            if idempotency_key:
                return Payment.objects.get(idempotency_key=idempotency_key)
            raise

        _recompute(order)
        record_audit("payment.refunded", entity_type="order", entity_id=order_id,
                     changes={"amount": str(amount), "reason": reason})
        transaction.on_commit(lambda: broadcast_tenant_event("payment_captured"))
        transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
    return refund
