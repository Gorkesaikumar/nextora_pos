"""Inventory Django Admin."""
from django.contrib import admin

from .models import (
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
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_default", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["is_active", "is_default"]


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "phone", "email", "gstin", "credit_days", "is_active"]
    search_fields = ["name", "code", "gstin", "phone"]
    list_filter = ["is_active"]


# ---------------------------------------------------------------------------
# Inventory Item
# ---------------------------------------------------------------------------
class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    fields = ["batch_number", "expiry_date", "quantity", "unit_cost", "is_active"]
    readonly_fields = ["quantity"]


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = [
        "movement_type", "quantity", "unit_cost", "balance_after",
        "reference_type", "reference_number", "performed_by_id", "created_at",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        "product_sku", "product_name", "warehouse", "quantity_on_hand",
        "quantity_reserved", "minimum_stock", "average_cost", "is_active",
    ]
    search_fields = ["product_sku", "product_name"]
    list_filter = ["warehouse", "is_active"]
    readonly_fields = ["quantity_on_hand", "quantity_reserved", "quantity_on_order", "average_cost"]
    inlines = [BatchInline, StockMovementInline]


# ---------------------------------------------------------------------------
# Purchase Orders
# ---------------------------------------------------------------------------
class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    readonly_fields = ["quantity_received", "line_total"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "supplier", "warehouse", "status",
        "total_amount", "expected_delivery_date", "created_at",
    ]
    search_fields = ["order_number", "supplier__name"]
    list_filter = ["status", "warehouse"]
    readonly_fields = ["order_number", "subtotal", "tax_amount", "total_amount"]
    inlines = [PurchaseOrderLineInline]


# ---------------------------------------------------------------------------
# Stock Transfers
# ---------------------------------------------------------------------------
class StockTransferLineInline(admin.TabularInline):
    model = StockTransferLine
    extra = 0
    readonly_fields = ["quantity_dispatched", "quantity_received"]


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = [
        "transfer_number", "from_warehouse", "to_warehouse",
        "status", "dispatched_at", "received_at",
    ]
    search_fields = ["transfer_number"]
    list_filter = ["status", "from_warehouse", "to_warehouse"]
    readonly_fields = ["transfer_number", "dispatched_at", "received_at"]
    inlines = [StockTransferLineInline]


# ---------------------------------------------------------------------------
# Stock Adjustments
# ---------------------------------------------------------------------------
class StockAdjustmentLineInline(admin.TabularInline):
    model = StockAdjustmentLine
    extra = 0
    readonly_fields = ["quantity_before", "unit_cost"]


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        "adjustment_number", "warehouse", "reason",
        "is_approved", "approved_at", "created_at",
    ]
    search_fields = ["adjustment_number"]
    list_filter = ["reason", "is_approved", "warehouse"]
    readonly_fields = ["adjustment_number", "is_approved", "approved_at"]
    inlines = [StockAdjustmentLineInline]


# ---------------------------------------------------------------------------
# Damaged Stock
# ---------------------------------------------------------------------------
@admin.register(DamagedStock)
class DamagedStockAdmin(admin.ModelAdmin):
    list_display = [
        "inventory_item", "warehouse", "quantity", "damage_reason",
        "incident_date", "reported_by_id",
    ]
    search_fields = ["inventory_item__product_sku", "damage_reason"]
    list_filter = ["warehouse", "incident_date"]
    readonly_fields = ["unit_cost", "reported_by_id", "adjustment"]


# ---------------------------------------------------------------------------
# Inventory Alerts
# ---------------------------------------------------------------------------
@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = [
        "inventory_item", "alert_type", "status", "quantity_at_alert",
        "threshold_value", "expiry_date", "created_at",
    ]
    search_fields = ["inventory_item__product_sku", "inventory_item__product_name"]
    list_filter = ["alert_type", "status"]
    readonly_fields = [
        "inventory_item", "batch", "alert_type", "quantity_at_alert",
        "threshold_value", "expiry_date", "acknowledged_at", "resolved_at",
    ]
