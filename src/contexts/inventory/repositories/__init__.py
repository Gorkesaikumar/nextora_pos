"""Repository layer for the inventory context.

Repositories encapsulate **all** ORM access for inventory aggregates so the
service/ledger layer stays free of query construction. Every query runs through
the tenant-scoped managers (fail-closed: no tenant context → empty queryset),
and ``lock``/``select_for_update`` helpers are provided for the serialized
write paths the stock ledger depends on.
"""
from .adjustment_repository import (
    DamagedStockRepository,
    StockAdjustmentLineRepository,
    StockAdjustmentRepository,
)
from .alert_repository import InventoryAlertRepository
from .batch_repository import BatchRepository
from .item_repository import InventoryItemRepository
from .movement_repository import StockMovementRepository
from .purchase_repository import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
)
from .supplier_repository import SupplierRepository
from .transfer_repository import (
    StockTransferLineRepository,
    StockTransferRepository,
)
from .warehouse_repository import WarehouseRepository

__all__ = [
    "BatchRepository",
    "DamagedStockRepository",
    "InventoryAlertRepository",
    "InventoryItemRepository",
    "PurchaseOrderLineRepository",
    "PurchaseOrderRepository",
    "StockAdjustmentLineRepository",
    "StockAdjustmentRepository",
    "StockMovementRepository",
    "StockTransferLineRepository",
    "StockTransferRepository",
    "SupplierRepository",
    "WarehouseRepository",
]
