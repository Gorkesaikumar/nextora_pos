"""Inventory API URL routing."""
from rest_framework.routers import DefaultRouter

from .views import (
    BatchViewSet,
    DamagedStockViewSet,
    InventoryAlertViewSet,
    InventoryItemViewSet,
    PurchaseOrderViewSet,
    StockAdjustmentViewSet,
    StockTransferViewSet,
    SupplierViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("items", InventoryItemViewSet, basename="inventory-item")
router.register("batches", BatchViewSet, basename="batch")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("transfers", StockTransferViewSet, basename="stock-transfer")
router.register("adjustments", StockAdjustmentViewSet, basename="stock-adjustment")
router.register("damaged", DamagedStockViewSet, basename="damaged-stock")
router.register("alerts", InventoryAlertViewSet, basename="inventory-alert")

urlpatterns = router.urls
