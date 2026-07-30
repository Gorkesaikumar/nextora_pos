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

    def create(self, request, *args, **kwargs):
        """Create a stock record and handle initial opening balance."""
        from decimal import Decimal
        from contexts.inventory.domain.enums import StockMovementType
        from contexts.inventory.services.item_service import ensure_item
        from contexts.inventory.services.movement_service import apply_stock_movement
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            item = ensure_item(
                product_id=d["product_id"],
                warehouse_id=d["warehouse"].id,
                product_sku=d["product_sku"],
                product_name=d["product_name"],
                minimum_stock=d.get("minimum_stock", Decimal("0")),
                reorder_point=d.get("reorder_point", Decimal("0")),
                reorder_quantity=d.get("reorder_quantity", Decimal("0")),
            )
            
            opening = d.get("opening_quantity") or Decimal("0")
            if opening > 0:
                apply_stock_movement(
                    inventory_item_id=item.id,
                    movement_type=StockMovementType.OPENING,
                    quantity=opening,
                    unit_cost=d.get("unit_cost") or Decimal("0"),
                    reference_type="opening_balance",
                    reference_number="OPENING",
                    performed_by_id=request.user.id,
                )
                
            try:
                from contexts.catalog.models import Product
                product = Product.objects.get(id=d["product_id"])
                if product.inventory_item_id != item.id:
                    product.inventory_item_id = item.id
                    product.save(update_fields=["inventory_item_id", "updated_at"])
            except Exception:
                pass
                
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        item.refresh_from_db()
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)


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

    @action(detail=False, methods=["get"], url_path="barcode-search")
    def barcode_search(self, request):
        """Find inventory items by product barcode or SKU."""
        from django.db import models
        barcode = request.query_params.get("barcode", "").strip()
        if not barcode:
            return Response(
                {"detail": "barcode query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        items = InventoryItem.objects.filter(product_sku__iexact=barcode)
        if not items.exists():
            try:
                from contexts.catalog.models import Product, ProductVariant
                products = Product.objects.filter(
                    models.Q(sku__iexact=barcode) | models.Q(barcode__iexact=barcode)
                )
                variants = ProductVariant.objects.filter(
                    models.Q(sku__iexact=barcode) | models.Q(barcode__iexact=barcode)
                )
                p_ids = [p.id for p in products] + [v.product_id for v in variants]
                if p_ids:
                    items = InventoryItem.objects.filter(product_id__in=p_ids)
            except Exception:
                pass

        if not items.exists():
            return Response(
                {"detail": f"No inventory item found for barcode '{barcode}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="ledger")
    def ledger(self, request, pk=None):
        """Retrieve stock ledger overview and recent transactions for an item."""
        item = self.get_object()
        movements = StockMovement.objects.filter(inventory_item=item).order_by("-created_at")
        page = self.paginate_queryset(movements)
        serializer = StockMovementSerializer(page if page is not None else movements, many=True)
        from contexts.inventory.repositories import StockMovementRepository
        ledger_sum = StockMovementRepository().balance_sum(item.id)
        data = {
            "inventory_item_id": str(item.id),
            "product_sku": item.product_sku,
            "quantity_on_hand": str(item.quantity_on_hand),
            "ledger_balance": str(ledger_sum),
            "transactions": serializer.data if page is None else self.get_paginated_response(serializer.data).data,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="reconcile")
    def reconcile(self, request, pk=None):
        """Perform stock ledger reconciliation against denormalized balance."""
        from contexts.inventory.services.ledger import reconcile_item
        try:
            result = reconcile_item(uuid.UUID(str(pk)))
            formatted = {
                "inventory_item_id": str(result["inventory_item_id"]),
                "on_hand": str(result["on_hand"]),
                "ledger_balance": str(result["ledger_balance"]),
                "discrepancy": str(result["discrepancy"]),
                "ok": result["ok"],
            }
            return Response(formatted, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

    @action(detail=False, methods=["get"], url_path="expiring-soon")
    def expiring_soon(self, request):
        """List active batches expiring within specified days (default 30)."""
        from django.utils import timezone
        from datetime import timedelta
        days = int(request.query_params.get("days", 30))
        today = timezone.now().date()
        cutoff = today + timedelta(days=days)
        batches = Batch.objects.filter(
            expiry_date__gt=today, expiry_date__lte=cutoff, quantity__gt=0, is_active=True
        ).order_by("expiry_date")
        page = self.paginate_queryset(batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(batches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="expired")
    def expired(self, request):
        """List batches that have already expired."""
        from django.utils import timezone
        today = timezone.now().date()
        batches = Batch.objects.filter(
            expiry_date__lte=today, quantity__gt=0, is_active=True
        ).order_by("expiry_date")
        page = self.paginate_queryset(batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(batches, many=True)
        return Response(serializer.data)


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

    @action(detail=True, methods=["post"], url_path="dispatch", url_name="dispatch")
    def dispatch_transfer_action(self, request, pk=None):
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

    @action(detail=False, methods=["post"], url_path="scan")
    def scan(self, request):
        """On-demand scanner to detect expiring batches and low stock items."""
        from contexts.inventory.services.alert_service import scan_expiring_batches, scan_low_stock_items
        days_ahead = int(request.data.get("days_ahead", 30))
        expiring_count = scan_expiring_batches(days_ahead=days_ahead)
        low_stock_count = scan_low_stock_items()
        return Response(
            {
                "new_expiring_alerts": expiring_count,
                "new_low_stock_alerts": low_stock_count,
            },
            status=status.HTTP_200_OK,
        )


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """ReadOnly viewset for browsing all stock movements across the inventory system."""
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["reference_number", "notes", "inventory_item__product_sku"]
    ordering_fields = ["created_at", "quantity"]

    def get_queryset(self):
        qs = StockMovement.objects.select_related("inventory_item", "batch")
        item_id = self.request.query_params.get("inventory_item_id")
        if item_id:
            qs = qs.filter(inventory_item_id=item_id)
        movement_type = self.request.query_params.get("movement_type")
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        return qs.order_by("-created_at")


class StockLedgerViewSet(viewsets.GenericViewSet):
    """System-wide Stock Ledger viewset for inventory audit and reconciliation."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        return InventoryItem.objects.all()

    def list(self, request):
        """List summary ledger balance across inventory items."""
        items = self.get_queryset().select_related("warehouse").filter(is_active=True)
        warehouse_id = request.query_params.get("warehouse_id")
        if warehouse_id:
            items = items.filter(warehouse_id=warehouse_id)

        from contexts.inventory.repositories import StockMovementRepository
        repo = StockMovementRepository()
        ledger_data = []
        for item in items[:100]:
            ledger_sum = repo.balance_sum(item.id)
            ledger_data.append(
                {
                    "inventory_item_id": str(item.id),
                    "warehouse": item.warehouse.code,
                    "product_sku": item.product_sku,
                    "product_name": item.product_name,
                    "quantity_on_hand": str(item.quantity_on_hand),
                    "ledger_balance": str(ledger_sum),
                    "in_sync": item.quantity_on_hand == ledger_sum,
                }
            )
        return Response(ledger_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="reconcile")
    def reconcile(self, request, pk=None):
        """Reconcile a specific item."""
        from contexts.inventory.services.ledger import reconcile_item
        try:
            result = reconcile_item(uuid.UUID(str(pk)))
            formatted = {
                "inventory_item_id": str(result["inventory_item_id"]),
                "on_hand": str(result["on_hand"]),
                "ledger_balance": str(result["ledger_balance"]),
                "discrepancy": str(result["discrepancy"]),
                "ok": result["ok"],
            }
            return Response(formatted, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
