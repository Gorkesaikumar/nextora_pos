"""Inventory API ViewSets."""
import uuid

from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.tenancy.context import get_current_tenant
from ..models import (
    Batch,
    DamagedStock,
    InventoryAlert,
    InventoryItem,
    PurchaseOrder,
    StockAdjustment,
    StockMovement,
    StockTransfer,
    Supplier,
    Warehouse,
)
from ..services import (
    acknowledge_alert,
    approve_and_apply_adjustment,
    create_adjustment,
    create_purchase_order,
    create_transfer,
    dispatch_transfer,
    receive_purchase_order,
    receive_transfer,
    record_damaged_stock,
    resolve_alert,
)
from .serializers import (
    AdjustmentLineInputSerializer,
    BatchSerializer,
    DamagedStockCreateSerializer,
    DamagedStockSerializer,
    InventoryAlertSerializer,
    InventoryItemSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderReceiveSerializer,
    PurchaseOrderSerializer,
    StockAdjustmentCreateSerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
    StockTransferCreateSerializer,
    StockTransferSerializer,
    SupplierSerializer,
    WarehouseSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Warehouse.objects.all()


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code", "gstin", "phone", "email"]

    def get_queryset(self):
        return Supplier.objects.all()


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["product_sku", "product_name"]

    def get_queryset(self):
        qs = InventoryItem.objects.select_related("warehouse")
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        low_stock = self.request.query_params.get("low_stock")
        if low_stock:
            from django.db.models import F
            qs = qs.filter(quantity_on_hand__lte=F("minimum_stock"), minimum_stock__gt=0)
        return qs

    @action(detail=True, methods=["get"], url_path="movements")
    def movements(self, request, pk=None):
        """List stock movements for this inventory item."""
        item = self.get_object()
        movements = StockMovement.objects.filter(inventory_item=item).order_by("-created_at")
        page = self.paginate_queryset(movements)
        if page is not None:
            serializer = StockMovementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="batches")
    def batches(self, request, pk=None):
        """List all batches for this inventory item."""
        item = self.get_object()
        batches = Batch.objects.filter(inventory_item=item).order_by("expiry_date")
        serializer = BatchSerializer(batches, many=True)
        return Response(serializer.data)


class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Batch.objects.select_related("inventory_item")
        expiring_soon = self.request.query_params.get("expiring_soon_days")
        if expiring_soon:
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            cutoff = today + timedelta(days=int(expiring_soon))
            qs = qs.filter(expiry_date__lte=cutoff, expiry_date__gt=today, quantity__gt=0)
        return qs


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["order_number", "supplier__name"]

    def get_queryset(self):
        return PurchaseOrder.objects.select_related("supplier", "warehouse").prefetch_related("lines")

    def create(self, request):
        """Create a new purchase order."""
        tenant_id = get_current_tenant()
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            po = create_purchase_order(
                tenant_id=tenant_id,
                supplier_id=d["supplier_id"],
                warehouse_id=d["warehouse_id"],
                lines=d["lines"],
                expected_delivery_date=d.get("expected_delivery_date"),
                notes=d.get("notes", ""),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        """Record stock received against this purchase order."""
        serializer = PurchaseOrderReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            po = receive_purchase_order(
                purchase_order_id=uuid.UUID(pk),
                receipts=serializer.validated_data["receipts"],
                received_by_id=request.user.id,
            )
        except (ValueError, InventoryItem.DoesNotExist) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_200_OK)


class StockTransferViewSet(viewsets.ModelViewSet):
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StockTransfer.objects.select_related(
            "from_warehouse", "to_warehouse"
        ).prefetch_related("lines")

    def create(self, request):
        tenant_id = get_current_tenant()
        serializer = StockTransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            transfer = create_transfer(
                tenant_id=tenant_id,
                from_warehouse_id=d["from_warehouse_id"],
                to_warehouse_id=d["to_warehouse_id"],
                lines=d["lines"],
                expected_date=d.get("expected_date"),
                notes=d.get("notes", ""),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StockTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch(self, request, pk=None):
        """Dispatch a transfer — moves stock to IN_TRANSIT."""
        try:
            transfer = dispatch_transfer(
                transfer_id=uuid.UUID(pk),
                dispatched_by_id=request.user.id,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StockTransferSerializer(transfer).data)

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        """Confirm receipt at destination — closes the transfer."""
        try:
            transfer = receive_transfer(
                transfer_id=uuid.UUID(pk),
                received_by_id=request.user.id,
            )
        except (ValueError, InventoryItem.DoesNotExist) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StockTransferSerializer(transfer).data)


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    serializer_class = StockAdjustmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StockAdjustment.objects.select_related("warehouse").prefetch_related("lines")

    def create(self, request):
        tenant_id = get_current_tenant()
        serializer = StockAdjustmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            adjustment = create_adjustment(
                tenant_id=tenant_id,
                warehouse_id=d["warehouse_id"],
                reason=d["reason"],
                lines=d["lines"],
                notes=d.get("notes", ""),
                adjusted_by_id=request.user.id,
            )
        except (ValueError, InventoryItem.DoesNotExist) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StockAdjustmentSerializer(adjustment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve and apply a pending stock adjustment."""
        try:
            adjustment = approve_and_apply_adjustment(
                adjustment_id=uuid.UUID(pk),
                approved_by_id=request.user.id,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StockAdjustmentSerializer(adjustment).data)


class DamagedStockViewSet(viewsets.ModelViewSet):
    serializer_class = DamagedStockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DamagedStock.objects.select_related("inventory_item", "warehouse", "batch")

    def create(self, request):
        tenant_id = get_current_tenant()
        serializer = DamagedStockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            damaged = record_damaged_stock(
                tenant_id=tenant_id,
                inventory_item_id=d["inventory_item_id"],
                warehouse_id=d["warehouse_id"],
                quantity=d["quantity"],
                damage_reason=d["damage_reason"],
                incident_date=d["incident_date"],
                batch_id=d.get("batch_id"),
                reported_by_id=request.user.id,
                image=d.get("image"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DamagedStockSerializer(damaged).data, status=status.HTTP_201_CREATED)


class InventoryAlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InventoryAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = InventoryAlert.objects.select_related("inventory_item", "batch")
        alert_type = self.request.query_params.get("type")
        alert_status = self.request.query_params.get("status")
        if alert_type:
            qs = qs.filter(alert_type=alert_type)
        if alert_status:
            qs = qs.filter(status=alert_status)
        return qs

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        """Acknowledge an open alert."""
        try:
            alert = acknowledge_alert(
                alert_id=uuid.UUID(pk),
                acknowledged_by_id=request.user.id,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InventoryAlertSerializer(alert).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        """Mark an alert as resolved."""
        alert = resolve_alert(alert_id=uuid.UUID(pk))
        return Response(InventoryAlertSerializer(alert).data)
