"""Inventory domain events.

Immutable, past-tense facts published through the shared transactional outbox
(``shared.infrastructure.events``). Events are written to the outbox inside the
same transaction as the stock change, then delivered to handlers after commit —
so a stock write and its event can never diverge.

Importing this package (done in ``InventoryConfig.ready``) registers handlers.
"""
from .domain_events import (
    LowStockDetected,
    StockAdjusted,
    StockConsumed,
    StockReceived,
    StockTransferred,
)
from .publisher import (
    publish_low_stock_detected,
    publish_stock_adjusted,
    publish_stock_consumed,
    publish_stock_received,
    publish_stock_transferred,
)

# Importing handlers registers them with the shared event registry.
from . import handlers  # noqa: F401  (side-effect import)

__all__ = [
    "LowStockDetected",
    "StockAdjusted",
    "StockConsumed",
    "StockReceived",
    "StockTransferred",
    "publish_low_stock_detected",
    "publish_stock_adjusted",
    "publish_stock_consumed",
    "publish_stock_received",
    "publish_stock_transferred",
]
