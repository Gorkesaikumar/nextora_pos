from decimal import Decimal
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contexts.catalog.models import ComboOffer, Modifier, Product, ProductVariant
from contexts.identity.api.permissions import RequirePermission
from contexts.ordering.api.serializers import (
    InvoiceSerializer,
    KOTSerializer,
    OrderSerializer,
    PaymentSerializer,
    PrintJobSerializer,
)
from contexts.ordering.domain.enums import ItemStatus, KOTStatus, OrderStatus
from contexts.ordering.models import KOT, Invoice, Order, Payment, PrintJob
from contexts.ordering.services import (
    discount_service,
    kot_service,
    order_service,
    payment_service,
)
from contexts.ordering.services.checkout_service import complete_checkout_transaction
from contexts.restaurant.services import table_service
from shared.api.permissions import BasePermission
from shared.api.views import BaseModelViewSet


class OrderViewSet(BaseModelViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ["status", "table_id", "type", "location_id"]
    search_fields = ["order_number", "customer_name", "customer_phone"]
    ordering_fields = ["opened_at", "total", "order_number"]

    def get_queryset(self) -> Any:
        return Order.objects.prefetch_related("items", "payments").all()

    def get_permissions(self) -> list[Any]:
        action_map = {
            "list": "orders.view",
            "retrieve": "orders.view",
            "create": "orders.create",
            "destroy": "orders.void",
            "add_item": "orders.update",
            "remove_item": "orders.update",
            "void_item": "orders.update",
            "update_item": "orders.update",
            "update_quantity": "orders.update",
            "apply_modifiers": "orders.update",
            "apply_combo": "orders.update",
            "remove_combo": "orders.update",
            "clear_cart": "orders.update",
            "clear": "orders.update",
            "notes": "orders.update",
            "discount": "orders.discount",
            "apply_discount": "orders.discount",
            "summary": "orders.view",
            "taxes": "orders.view",
            "print_queue": "orders.view",
            "payment_history": "orders.view",
            "timeline": "orders.view",
            "pay": "payments.capture",
            "refund": "payments.refund",
            "void": "orders.void",
            "status": "orders.update",
            "send_kot": "orders.update",
            "assign_table": "orders.update",
            "release_table": "orders.update",
            "move_table": "orders.update",
            "merge_table": "orders.update",
            "split_table": "orders.update",
            "receipt": "orders.view",
            "invoice": "orders.view",
            "split": "orders.update",
            "merge": "orders.update",
        }
        permission_code = action_map.get(self.action, "orders.view")
        return [IsAuthenticated(), BasePermission(), RequirePermission(permission_code)()]

    def create(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        order_type = request.data.get("type")
        table_id = request.data.get("table_id")
        is_interstate = request.data.get("is_interstate", False)
        service_charge_rate = Decimal(str(request.data.get("service_charge_rate", "0")))

        if not order_type:
            return Response(
                {"detail": "type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tbl_uuid = uuid.UUID(table_id) if table_id else None

        order = order_service.create_order(
            order_type=order_type,
            table_id=tbl_uuid,
            is_interstate=is_interstate,
            service_charge_rate=service_charge_rate,
            created_by=request.user.id if request.user else None,
        )

        # Seat guests automatically if table is assigned
        if tbl_uuid:
            try:
                table_service.seat_guests(tbl_uuid)
            except Exception:
                pass

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        order = self.get_object()
        if order.status == OrderStatus.SETTLED:
            return Response(
                {"detail": "Cannot void a settled order."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order_service.void_order(order.id, "Deleted via API")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def add_item(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        product_id = request.data.get("product_id")
        variant_id = request.data.get("variant_id")
        qty = Decimal(str(request.data.get("qty", "1")))
        notes = request.data.get("notes", "")

        if not product_id:
            return Response(
                {"detail": "product_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
            except ProductVariant.DoesNotExist:
                return Response(
                    {"detail": "Product variant not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        order_service.add_item(
            order_id=order.id,
            product=product,
            variant=variant,
            qty=qty,
            notes=notes,
        )

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="remove-item")
    def remove_item(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        item_id = request.data.get("item_id")

        if not item_id:
            return Response(
                {"detail": "item_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_service.void_item(order.id, uuid.UUID(item_id))
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def void_item(self, request: Any, pk: Any = None) -> Response:
        return self.remove_item(request, pk)

    @action(detail=True, methods=["post"], url_path="update-item")
    def update_item(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        item_id = request.data.get("item_id")
        notes = request.data.get("notes", "")
        modifier_ids = request.data.get("modifiers", [])

        if not item_id:
            return Response(
                {"detail": "item_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        modifiers = list(Modifier.objects.filter(id__in=modifier_ids))

        order_service.update_item_modifiers(
            order_id=order.id,
            item_id=uuid.UUID(item_id),
            modifiers=modifiers,
            notes=notes,
        )

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="update-quantity")
    def update_quantity(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        item_id = request.data.get("item_id")
        qty = Decimal(str(request.data.get("qty", "1")))

        if not item_id:
            return Response(
                {"detail": "item_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_service.set_item_qty(order.id, uuid.UUID(item_id), qty)
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="apply-modifiers")
    def apply_modifiers(self, request: Any, pk: Any = None) -> Response:
        return self.update_item(request, pk)

    @action(detail=True, methods=["post"], url_path="apply-combo")
    def apply_combo(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        combo_offer_id = request.data.get("combo_offer_id")
        selections_data = request.data.get("selections")

        if not combo_offer_id:
            return Response(
                {"detail": "combo_offer_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            combo_offer = ComboOffer.objects.get(id=combo_offer_id)
        except ComboOffer.DoesNotExist:
            return Response(
                {"detail": "Combo offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if selections_data is not None and isinstance(selections_data, list):
            # Manual combo adding
            selections = []
            for sel in selections_data:
                product_id = sel.get("product_id")
                variant_id = sel.get("variant_id")
                modifier_ids = sel.get("modifiers", [])
                qty = Decimal(str(sel.get("qty", "1")))
                notes = sel.get("notes", "")

                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    return Response(
                        {"detail": f"Product {product_id} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                variant = None
                if variant_id:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id, product=product)
                    except ProductVariant.DoesNotExist:
                        return Response(
                            {"detail": f"Variant {variant_id} not found for product {product_id}."},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                modifiers = list(Modifier.objects.filter(id__in=modifier_ids))

                selections.append({
                    "product": product,
                    "variant": variant,
                    "modifiers": modifiers,
                    "qty": qty,
                    "notes": notes,
                })
            order_service.add_combo(order.id, combo_offer, selections)
        else:
            # Retrospective matching combo
            try:
                discount_service.apply_retrospective_combo(order.id, combo_offer.id)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="remove-combo")
    def remove_combo(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        combo_id = request.data.get("combo_id")
        if not combo_id:
            return Response(
                {"detail": "combo_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order_service.remove_combo(order.id, uuid.UUID(str(combo_id)))
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="clear-cart")
    def clear_cart(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        if order.status != OrderStatus.OPEN:
            return Response(
                {"detail": "Can only clear items on an open order/cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.items.filter(status=ItemStatus.ACTIVE).update(status=ItemStatus.VOID)
        order_service.recalculate(order)
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def notes(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        item_id = request.data.get("item_id")
        notes = request.data.get("notes", "")

        if not item_id:
            return Response(
                {"detail": "item_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = order.items.get(id=item_id, status=ItemStatus.ACTIVE)
        item.notes = notes
        item.save(update_fields=["notes", "updated_at"])

        try:
            from shared.tenancy.context import get_current_tenant
            from contexts.ordering.realtime import broadcast_tenant_event
            tid = get_current_tenant()
            broadcast_tenant_event("order_changed", tenant_id=tid)
        except Exception:
            pass

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def discount(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        discount_type_raw = request.data.get("discount_type")
        value = Decimal(str(request.data.get("value", "0")))

        if not discount_type_raw:
            return Response(
                {"detail": "discount_type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Map to internal DiscountType choices (flat, percent)
        discount_type = discount_type_raw.lower()
        if discount_type in ("percent", "percentage", "staff"):
            internal_type = "percent"
        elif discount_type in ("flat", "fixed", "coupon"):
            internal_type = "flat"
        else:
            internal_type = "none"

        order_service.apply_discount(order.id, internal_type, value)
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def apply_discount(self, request: Any, pk: Any = None) -> Response:
        return self.discount(request, pk)

    @action(detail=True, methods=["get"])
    def summary(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        summary_data = {
            "subtotal": str(order.subtotal),
            "discount_amount": str(order.discount_amount),
            "service_charge_amount": str(order.service_charge_amount),
            "taxable_amount": str(order.taxable_amount),
            "cgst": str(order.cgst),
            "sgst": str(order.sgst),
            "igst": str(order.igst),
            "cess": str(order.cess),
            "tax_amount": str(order.tax_amount),
            "round_off": str(order.round_off),
            "total": str(order.total),
        }
        return Response(summary_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="taxes")
    def taxes(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        items = order.items.filter(status=ItemStatus.ACTIVE)
        item_taxes = [
            {
                "item_id": str(item.id),
                "name": item.name_snapshot,
                "tax_rate": str(item.tax_rate),
                "cess_rate": str(item.cess_rate),
                "hsn_code": item.hsn_code,
                "line_subtotal": str(item.line_subtotal),
                "line_total": str(item.line_total),
            }
            for item in items
        ]
        data = {
            "order_id": str(order.id),
            "is_interstate": order.is_interstate,
            "taxable_amount": str(order.taxable_amount),
            "cgst": str(order.cgst),
            "sgst": str(order.sgst),
            "igst": str(order.igst),
            "cess": str(order.cess),
            "tax_amount": str(order.tax_amount),
            "item_taxes": item_taxes,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="print-queue")
    def print_queue(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        jobs = PrintJob.objects.filter(order=order)
        serializer = PrintJobSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="payment-history")
    def payment_history(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        payments = order.payments.all().order_by("-captured_at")
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        events = []

        # Base order opened event
        events.append(
            {
                "event_type": "order.opened",
                "description": f"Order #{order.order_number} opened ({order.type})",
                "timestamp": order.opened_at.isoformat() if order.opened_at else None,
                "actor_id": str(order.created_by) if order.created_by else None,
                "metadata": {"status": order.status, "total": str(order.total)},
            }
        )

        try:
            from contexts.audit.models import AuditLog
            audits = AuditLog.objects.filter(
                entity_type="order", entity_id=order.id
            ).order_by("occurred_at")
            for a in audits:
                if a.action == "order.created":
                    continue
                events.append(
                    {
                        "event_type": a.action,
                        "description": f"Action {a.action} executed on order",
                        "timestamp": a.occurred_at.isoformat() if a.occurred_at else None,
                        "actor_id": str(a.actor_id) if a.actor_id else None,
                        "metadata": {
                            "reason": a.reason,
                            "old_value": a.old_value,
                            "new_value": a.new_value,
                        },
                    }
                )
        except Exception:
            pass

        for kot in order.kots.all():
            events.append(
                {
                    "event_type": "kot.created",
                    "description": f"KOT #{kot.number} generated",
                    "timestamp": kot.created_at_kot.isoformat() if kot.created_at_kot else None,
                    "actor_id": None,
                    "metadata": {"status": kot.status, "items_count": kot.items.count()},
                }
            )

        for payment in order.payments.all():
            events.append(
                {
                    "event_type": f"payment.{payment.kind}",
                    "description": f"{payment.kind.capitalize()} of {payment.amount} via {payment.method}",
                    "timestamp": payment.captured_at.isoformat() if payment.captured_at else None,
                    "actor_id": str(payment.created_by) if payment.created_by else None,
                    "metadata": {
                        "reference": payment.reference,
                        "status": payment.status,
                        "refund_reason": payment.refund_reason,
                    },
                }
            )

        invoice = getattr(order, "invoice", None)
        if not invoice:
            invoice = Invoice.objects.filter(order=order).first()
        if invoice and invoice.issued_at:
            events.append(
                {
                    "event_type": "invoice.issued",
                    "description": f"Invoice #{invoice.number or invoice.id} generated",
                    "timestamp": invoice.issued_at.isoformat(),
                    "actor_id": None,
                    "metadata": {"total": str(invoice.total), "status": invoice.status},
                }
            )

        if order.settled_at:
            events.append(
                {
                    "event_type": "order.settled",
                    "description": "Order successfully settled and closed",
                    "timestamp": order.settled_at.isoformat(),
                    "actor_id": None,
                    "metadata": {"paid_amount": str(order.paid_amount)},
                }
            )
        elif order.voided_at:
            events.append(
                {
                    "event_type": "order.voided",
                    "description": f"Order voided: {order.void_reason}",
                    "timestamp": order.voided_at.isoformat(),
                    "actor_id": None,
                    "metadata": {"reason": order.void_reason},
                }
            )

        events.sort(key=lambda x: x["timestamp"] or "")
        return Response({"order_id": str(order.id), "timeline": events}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def pay(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        amount_raw = request.data.get("amount")
        method = request.data.get("method")
        idempotency_key = request.data.get("idempotency_key", "")
        reference = request.data.get("reference", "")
        tendered_raw = request.data.get("tendered")

        if not amount_raw or not method:
            return Response(
                {"detail": "amount and method are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = Decimal(str(amount_raw))
        tendered = Decimal(str(tendered_raw)) if tendered_raw else amount

        # If it's a full payment or completes the outstanding balance
        if amount >= order.due_amount:
            try:
                # Perform atomic complete checkout transaction
                order, invoice, print_jobs, print_result = complete_checkout_transaction(
                    order_id=order.id,
                    method=method,
                    tendered=tendered,
                    performed_by_id=request.user.id if request.user else None,
                    idempotency_key=idempotency_key,
                )
                payment = order.payments.filter(kind="payment").order_by("-captured_at").first()
                serializer = PaymentSerializer(payment)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Record partial payment
            payment = payment_service.add_payment(
                order_id=order.id,
                amount=amount,
                method=method,
                idempotency_key=idempotency_key,
                reference=reference,
                tendered=tendered,
                created_by=request.user.id if request.user else None,
            )
            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def refund(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        amount = Decimal(str(request.data.get("amount")))
        method = request.data.get("method")
        reason = request.data.get("reason", "")
        idempotency_key = request.data.get("idempotency_key", "")

        if not amount or not method:
            return Response(
                {"detail": "amount and method are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund = payment_service.refund_payment(
            order_id=order.id,
            amount=amount,
            method=method,
            reason=reason,
            idempotency_key=idempotency_key,
            created_by=request.user.id if request.user else None,
        )

        serializer = PaymentSerializer(refund)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def void(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        reason = request.data.get("reason", "")

        if not reason:
            return Response(
                {"detail": "reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        voided = order_service.void_order(order.id, reason)
        serializer = self.get_serializer(voided)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def status(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        new_status = request.data.get("status")
        reason = request.data.get("reason", "")

        if not new_status:
            return Response(
                {"detail": "status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = new_status.lower()
        current_status = order.status

        if new_status in ("draft", "open"):
            if current_status == OrderStatus.VOID:
                return Response(
                    {"detail": "Cannot reopen a voided order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if current_status == OrderStatus.SETTLED:
                return Response(
                    {"detail": "Cannot reopen a settled order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order.status = OrderStatus.OPEN
            order.save(update_fields=["status", "updated_at"])

        elif new_status == "preparing":
            if current_status != OrderStatus.OPEN:
                return Response(
                    {"detail": "Order must be open to start preparing."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order.kots.filter(status=KOTStatus.NEW).update(status=KOTStatus.PREPARING)

        elif new_status == "ready":
            if current_status != OrderStatus.OPEN:
                return Response(
                    {"detail": "Order must be open to be ready."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order.kots.filter(status__in=[KOTStatus.NEW, KOTStatus.PREPARING]).update(
                status=KOTStatus.READY
            )

        elif new_status == "served":
            if current_status != OrderStatus.OPEN:
                return Response(
                    {"detail": "Order must be open to be served."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order.kots.filter(
                status__in=[KOTStatus.NEW, KOTStatus.PREPARING, KOTStatus.READY]
            ).update(status=KOTStatus.SERVED)

        elif new_status == "completed":
            if order.due_amount > 0:
                return Response(
                    {"detail": f"Order has outstanding due of {order.due_amount}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from contexts.ordering.services.invoice_service import settle_and_invoice

            settle_and_invoice(order.id)

        elif new_status in ("cancelled", "void"):
            if current_status == OrderStatus.SETTLED:
                return Response(
                    {"detail": "Cannot void a settled order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order_service.void_order(order.id, reason or "Voided via status transition")

        else:
            return Response(
                {"detail": f"Invalid status: {new_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="send-kot")
    def send_kot(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        kots = kot_service.generate_kots(order.id)
        serializer = KOTSerializer(kots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-table")
    def assign_table(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        table_id = request.data.get("table_id")
        if not table_id:
            return Response(
                {"detail": "table_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from contexts.restaurant.models.layout import DiningTable

        try:
            table = DiningTable.objects.get(id=table_id)
        except DiningTable.DoesNotExist:
            return Response(
                {"detail": "Table not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        order.table_id = table.id
        order.save(update_fields=["table_id", "updated_at"])

        try:
            table_service.seat_guests(table.id)
        except Exception:
            pass

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="release-table")
    def release_table(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        table_id = order.table_id
        if not table_id:
            return Response(
                {"detail": "No table is currently assigned to this order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.table_id = None
        order.save(update_fields=["table_id", "updated_at"])

        try:
            table_service.release_table(table_id)
        except Exception:
            pass

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="move-table")
    def move_table(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        new_table_id = request.data.get("new_table_id")
        if not new_table_id:
            return Response(
                {"detail": "new_table_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_table_id = order.table_id

        from contexts.restaurant.models.layout import DiningTable

        try:
            new_table = DiningTable.objects.get(id=new_table_id)
        except DiningTable.DoesNotExist:
            return Response(
                {"detail": "New table not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            order.table_id = new_table.id
            order.save(update_fields=["table_id", "updated_at"])
            if old_table_id:
                try:
                    table_service.release_table(old_table_id)
                except Exception:
                    pass
            try:
                table_service.seat_guests(new_table.id)
            except Exception:
                pass

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="merge-table")
    def merge_table(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        secondary_table_ids = request.data.get("secondary_table_ids", [])
        if not order.table_id:
            return Response(
                {"detail": "This order does not have an assigned primary table."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            table_service.merge_tables(
                order.table_id, [uuid.UUID(t) for t in secondary_table_ids]
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="split-table")
    def split_table(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        if not order.table_id:
            return Response(
                {"detail": "This order does not have an assigned primary table."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            table_service.split_tables(order.table_id)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def receipt(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        invoice = getattr(order, "invoice", None)
        if not invoice:
            invoice = Invoice.objects.filter(order=order).first()

        if not invoice:
            return Response(
                {"detail": "No invoice found for this order. Settle the order first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from contexts.ordering.services.receipt_data_mapper import build_receipt_payload

        payload = build_receipt_payload(order, invoice)

        jobs = PrintJob.objects.filter(order=order, invoice=invoice)
        jobs_serializer = PrintJobSerializer(jobs, many=True)

        return Response(
            {"receipt_payload": payload, "print_jobs": jobs_serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def invoice(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        invoice = getattr(order, "invoice", None)
        if not invoice:
            invoice = Invoice.objects.filter(order=order).first()

        if not invoice:
            return Response(
                {"detail": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def split(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        moves = request.data.get("moves")

        if not moves or not isinstance(moves, list):
            return Response(
                {"detail": "moves list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = order_service.split_order(order.id, moves)
        serializer = self.get_serializer(target)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def merge(self, request: Any, pk: Any = None) -> Response:
        order = self.get_object()
        source_ids_raw = request.data.get("source_ids")

        if not source_ids_raw or not isinstance(source_ids_raw, list):
            return Response(
                {"detail": "source_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_uuids = [uuid.UUID(s) for s in source_ids_raw]
        merged = order_service.merge_orders(order.id, source_uuids)
        serializer = self.get_serializer(merged)
        return Response(serializer.data, status=status.HTTP_200_OK)


class KOTViewSet(BaseModelViewSet):
    serializer_class = KOTSerializer
    filterset_fields = ["order", "kitchen_station_id", "status"]
    search_fields = ["number"]
    ordering_fields = ["created_at_kot", "number"]

    def get_queryset(self) -> Any:
        return KOT.objects.prefetch_related("items").all()

    def get_permissions(self) -> list[Any]:
        read_only = self.action in {"list", "retrieve"}
        code = "orders.view" if read_only else "orders.update"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]

    @action(detail=True, methods=["patch"])
    def status(self, request: Any, pk: Any = None) -> Response:
        kot = self.get_object()
        new_status = request.data.get("status")
        if not new_status or new_status not in [c[0] for c in KOTStatus.choices]:
            return Response(
                {"detail": "Invalid or missing status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kot.status = new_status
        kot.save(update_fields=["status", "updated_at"])

        try:
            from django.db import transaction
            from contexts.ordering.realtime import broadcast_tenant_event
            from shared.tenancy.context import get_current_tenant

            tid = get_current_tenant()
            transaction.on_commit(
                lambda: broadcast_tenant_event("kds_changed", tenant_id=tid)
            )
            transaction.on_commit(
                lambda: broadcast_tenant_event("order_changed", tenant_id=tid)
            )
        except Exception:
            pass

        serializer = self.get_serializer(kot)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def print(self, request: Any, pk: Any = None) -> Response:
        kot = self.get_object()
        
        from contexts.ordering.models import PrintJob
        from contexts.ordering.domain.enums import PrintJobType, PrintJobStatus
        from contexts.ordering.services.printing import execute_print_job
        
        # Find existing KOT print job or create a new one
        job = PrintJob.objects.filter(kot=kot, job_type=PrintJobType.KOT_TICKET).last()
        
        if not job:
            from contexts.ordering.services.print_templates import KOTTemplate
            kot_tpl = KOTTemplate(paper_width="80mm")
            job = PrintJob.objects.create(
                order=kot.order,
                kot=kot,
                job_type=PrintJobType.KOT_TICKET,
                tenant=kot.order.tenant,
                content_text=kot_tpl.render_text(kot),
                content_escpos=kot_tpl.render_escpos(kot),
                status=PrintJobStatus.PENDING,
            )
            
        success = execute_print_job(job)
        
        if success:
            return Response({"success": True, "message": f"KOT #{kot.number} sent to printer."})
        else:
            return Response(
                {"success": False, "error": job.error_message or "Failed to print KOT."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CartViewSet(OrderViewSet):
    """API viewset specifically focused on managing active open orders as shopping carts."""

    def get_queryset(self) -> Any:
        return Order.objects.filter(status=OrderStatus.OPEN).prefetch_related("items", "payments").all()

    @action(detail=True, methods=["post"], url_path="clear")
    def clear(self, request: Any, pk: Any = None) -> Response:
        return self.clear_cart(request, pk)

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request: Any, pk: Any = None) -> Response:
        return self.pay(request, pk)


class PrintJobViewSet(BaseModelViewSet):
    """API viewset managing thermal receipt and KOT print queue jobs."""
    serializer_class = PrintJobSerializer
    filterset_fields = ["order", "status", "job_type"]
    search_fields = ["error_message"]
    ordering_fields = ["created_at", "retry_count"]

    def get_queryset(self) -> Any:
        return PrintJob.objects.select_related("order", "invoice", "kot").all()

    def get_permissions(self) -> list[Any]:
        code = "orders.view" if self.action in {"list", "retrieve"} else "orders.update"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]

    @action(detail=True, methods=["post"])
    def retry(self, request: Any, pk: Any = None) -> Response:
        job = self.get_object()
        from contexts.ordering.domain.enums import PrintJobStatus
        job.status = PrintJobStatus.PENDING
        job.retry_count = 0
        job.save(update_fields=["status", "retry_count", "updated_at"])
        serializer = self.get_serializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentViewSet(BaseModelViewSet):
    """API viewset for payment history, filtering, and transaction details across all orders."""
    serializer_class = PaymentSerializer
    filterset_fields = ["order", "kind", "method", "status"]
    search_fields = ["reference", "refund_reason", "idempotency_key"]
    ordering_fields = ["captured_at", "amount"]

    def get_queryset(self) -> Any:
        return Payment.objects.select_related("order").all()

    def get_permissions(self) -> list[Any]:
        code = "payments.view" if self.action in {"list", "retrieve"} else "payments.capture"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]
