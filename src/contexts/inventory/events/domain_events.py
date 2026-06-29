"""Inventory domain event definitions.

Each extends the shared :class:`DomainEvent` (which supplies ``event_id``,
``occurred_at``, ``tenant_id``, ``event_version`` — all defaulted, so subclass
fields must default too). Payloads stay JSON-safe: the dispatcher serialises
UUIDs/datetimes, and money/quantities are carried as strings.
"""
import uuid
from dataclasses import dataclass

from shared.domain.events import DomainEvent


@dataclass(frozen=True)
class StockReceived(DomainEvent):
    inventory_item_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    quantity: str = "0"
    unit_cost: str = "0"
    reference_type: str = ""
    reference_id: uuid.UUID | None = None
    reference_number: str = ""


@dataclass(frozen=True)
class StockConsumed(DomainEvent):
    inventory_item_id: uuid.UUID | None = None
    quantity: str = "0"
    reference_type: str = ""
    reference_id: uuid.UUID | None = None


@dataclass(frozen=True)
class StockTransferred(DomainEvent):
    transfer_id: uuid.UUID | None = None
    transfer_number: str = ""
    from_warehouse_id: uuid.UUID | None = None
    to_warehouse_id: uuid.UUID | None = None


@dataclass(frozen=True)
class StockAdjusted(DomainEvent):
    adjustment_id: uuid.UUID | None = None
    adjustment_number: str = ""
    reason: str = ""


@dataclass(frozen=True)
class LowStockDetected(DomainEvent):
    inventory_item_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    product_sku: str = ""
    quantity_on_hand: str = "0"
    minimum_stock: str = "0"
    out_of_stock: bool = False
