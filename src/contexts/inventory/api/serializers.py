"""Inventory API serializers."""
from rest_framework import serializers

from ..models import (
    Batch,
    DamagedStock,
    InventoryAlert,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderLine,
    StockAdjustment,
    StockAdjustmentLine,
    StockMovement,
    StockTransfer,
    StockTransferLine,
    Supplier,
    Warehouse,
)


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------
class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            "id", "name", "code", "address", "branch_id",
            "is_active", "is_default",
        ]
        read_only_fields = ["id"]


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id", "name", "code", "contact_person", "phone", "email",
            "address", "gstin", "pan", "bank_name", "bank_account_no",
            "bank_ifsc", "credit_days", "is_active",
        ]
        read_only_fields = ["id"]


# ---------------------------------------------------------------------------
# Inventory Item
# ---------------------------------------------------------------------------
class InventoryItemSerializer(serializers.ModelSerializer):
    quantity_available = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id", "product_id", "product_sku", "product_name", "warehouse",
            "quantity_on_hand", "quantity_reserved", "quantity_on_order",
            "quantity_available", "minimum_stock", "reorder_point",
            "reorder_quantity", "average_cost", "is_active",
        ]
        read_only_fields = [
            "id", "quantity_on_hand", "quantity_reserved",
            "quantity_on_order", "quantity_available", "average_cost",
        ]


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------
class BatchSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id", "inventory_item", "batch_number", "manufacture_date",
            "expiry_date", "quantity", "unit_cost", "purchase_order_id",
            "is_active", "is_expired",
        ]
        read_only_fields = ["id", "is_expired", "purchase_order_id"]


# ---------------------------------------------------------------------------
# Stock Movement
# ---------------------------------------------------------------------------
class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id", "inventory_item", "batch", "movement_type",
            "quantity", "unit_cost", "balance_after",
            "reference_type", "reference_id", "reference_number",
            "notes", "performed_by_id", "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------
class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    quantity_pending = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id", "inventory_item", "quantity_ordered", "quantity_received",
            "quantity_pending", "unit_cost", "tax_rate", "line_total",
        ]
        read_only_fields = ["id", "quantity_received", "quantity_pending", "line_total"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "supplier", "warehouse", "order_number", "status",
            "expected_delivery_date", "notes", "subtotal", "tax_amount",
            "total_amount", "approved_by_id", "approved_at",
            "lines", "created_at",
        ]
        read_only_fields = [
            "id", "order_number", "status", "subtotal",
            "tax_amount", "total_amount", "approved_at",
        ]


# ---------------------------------------------------------------------------
# Purchase Order Create Input
# ---------------------------------------------------------------------------
class PurchaseOrderLineInputSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity_ordered = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=0)
    tax_rate = serializers.DecimalField(max_digits=6, decimal_places=4, min_value=0, required=False, default=0)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = PurchaseOrderLineInputSerializer(many=True, min_length=1)


# ---------------------------------------------------------------------------
# Purchase Order Receive Input
# ---------------------------------------------------------------------------
class ReceiptLineSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    quantity_received = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0)
    batch_number = serializers.CharField(required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    manufacture_date = serializers.DateField(required=False, allow_null=True)


class PurchaseOrderReceiveSerializer(serializers.Serializer):
    receipts = ReceiptLineSerializer(many=True, min_length=1)


# ---------------------------------------------------------------------------
# Stock Transfer
# ---------------------------------------------------------------------------
class StockTransferLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransferLine
        fields = [
            "id", "inventory_item", "batch",
            "quantity_requested", "quantity_dispatched", "quantity_received",
        ]
        read_only_fields = ["id", "quantity_dispatched", "quantity_received"]


class StockTransferSerializer(serializers.ModelSerializer):
    lines = StockTransferLineSerializer(many=True, read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id", "transfer_number", "from_warehouse", "to_warehouse",
            "status", "expected_date", "dispatched_at", "received_at",
            "notes", "lines", "created_at",
        ]
        read_only_fields = [
            "id", "transfer_number", "status",
            "dispatched_at", "received_at",
        ]


class TransferLineInputSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity_requested = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    batch_id = serializers.UUIDField(required=False, allow_null=True)


class StockTransferCreateSerializer(serializers.Serializer):
    from_warehouse_id = serializers.UUIDField()
    to_warehouse_id = serializers.UUIDField()
    expected_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = TransferLineInputSerializer(many=True, min_length=1)


# ---------------------------------------------------------------------------
# Stock Adjustment
# ---------------------------------------------------------------------------
class StockAdjustmentLineSerializer(serializers.ModelSerializer):
    quantity_delta = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = StockAdjustmentLine
        fields = [
            "id", "inventory_item", "batch",
            "quantity_before", "quantity_after", "quantity_delta", "unit_cost",
        ]
        read_only_fields = ["id", "quantity_before", "quantity_delta", "unit_cost"]


class StockAdjustmentSerializer(serializers.ModelSerializer):
    lines = StockAdjustmentLineSerializer(many=True, read_only=True)

    class Meta:
        model = StockAdjustment
        fields = [
            "id", "adjustment_number", "warehouse", "reason", "notes",
            "adjusted_by_id", "approved_by_id", "is_approved", "approved_at",
            "lines", "created_at",
        ]
        read_only_fields = [
            "id", "adjustment_number", "adjusted_by_id",
            "is_approved", "approved_at",
        ]


class AdjustmentLineInputSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity_after = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0)
    batch_id = serializers.UUIDField(required=False, allow_null=True)


class StockAdjustmentCreateSerializer(serializers.Serializer):
    warehouse_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=30)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = AdjustmentLineInputSerializer(many=True, min_length=1)


# ---------------------------------------------------------------------------
# Damaged Stock
# ---------------------------------------------------------------------------
class DamagedStockSerializer(serializers.ModelSerializer):
    total_loss_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = DamagedStock
        fields = [
            "id", "inventory_item", "batch", "warehouse", "quantity",
            "unit_cost", "damage_reason", "incident_date",
            "reported_by_id", "total_loss_value", "image", "created_at",
        ]
        read_only_fields = ["id", "unit_cost", "reported_by_id", "total_loss_value"]


class DamagedStockCreateSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    damage_reason = serializers.CharField(max_length=255)
    incident_date = serializers.DateField()
    batch_id = serializers.UUIDField(required=False, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Inventory Alert
# ---------------------------------------------------------------------------
class InventoryAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryAlert
        fields = [
            "id", "inventory_item", "batch", "alert_type", "status",
            "message", "quantity_at_alert", "threshold_value", "expiry_date",
            "acknowledged_by_id", "acknowledged_at", "resolved_at", "created_at",
        ]
        read_only_fields = fields
