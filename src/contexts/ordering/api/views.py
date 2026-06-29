from decimal import Decimal
import uuid

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contexts.catalog.models import Product, ProductVariant
from contexts.identity.api.permissions import RequirePermission
from contexts.ordering.api.serializers import OrderSerializer, PaymentSerializer
from contexts.ordering.models import Order
from contexts.ordering.services import order_service, payment_service


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.prefetch_related("items", "payments").all()

    def get_permissions(self):
        # Map each action to the correct RBAC permission code from the catalog
        action_map = {
            "list": "orders.view",
            "retrieve": "orders.view",
            "create": "orders.create",
            "add_item": "orders.update",
            "void_item": "orders.update",
            "apply_discount": "orders.discount",
            "split": "orders.update",
            "merge": "orders.update",
            "void": "orders.void",
            "pay": "payments.capture",
            "refund": "payments.refund",
        }
        permission_code = action_map.get(self.action, "orders.view")
        return [IsAuthenticated(), RequirePermission(permission_code)()]

    def create(self, request, *args, **kwargs):
        location_id = request.data.get("location_id")
        order_type = request.data.get("type")
        table_id = request.data.get("table_id")
        is_interstate = request.data.get("is_interstate", False)
        service_charge_rate = Decimal(str(request.data.get("service_charge_rate", "0")))

        if not location_id or not order_type:
            return Response(
                {"detail": "location_id and type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loc_uuid = uuid.UUID(location_id)
        tbl_uuid = uuid.UUID(table_id) if table_id else None

        order = order_service.create_order(
            location_id=loc_uuid,
            order_type=order_type,
            table_id=tbl_uuid,
            is_interstate=is_interstate,
            service_charge_rate=service_charge_rate,
            created_by=request.user.id if request.user else None,
        )

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_item(self, request, pk=None):
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

        item = order_service.add_item(
            order_id=order.id,
            product=product,
            variant=variant,
            qty=qty,
            notes=notes,
        )

        # Refresh order instance to return updated totals
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def void_item(self, request, pk=None):
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
    def apply_discount(self, request, pk=None):
        order = self.get_object()
        discount_type = request.data.get("discount_type")
        value = Decimal(str(request.data.get("value", "0")))

        if not discount_type:
            return Response(
                {"detail": "discount_type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_service.apply_discount(order.id, discount_type, value)
        order.refresh_from_db()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def split(self, request, pk=None):
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
    def merge(self, request, pk=None):
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

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        order = self.get_object()
        amount = Decimal(str(request.data.get("amount")))
        method = request.data.get("method")
        idempotency_key = request.data.get("idempotency_key", "")
        reference = request.data.get("reference", "")
        tendered_raw = request.data.get("tendered")
        tendered = Decimal(str(tendered_raw)) if tendered_raw else None

        if not amount or not method:
            return Response(
                {"detail": "amount and method are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = payment_service.add_payment(
            order_id=order.id,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
            reference=reference,
            tendered=tendered,
            created_by=request.user.id if request.user else None,
        )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
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
    def void(self, request, pk=None):
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
