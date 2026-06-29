"""Publish inventory events through the shared transactional outbox.

Each helper stamps the active tenant and hands the event to the shared
dispatcher, which persists it to the outbox inside the current transaction and
schedules delivery on commit. Call these *inside* the service transaction that
made the change, so the event can never diverge from the stock write.
"""
import uuid
from decimal import Decimal
from typing import Optional

from shared.domain.events import DomainEvent
from shared.infrastructure.events.dispatcher import dispatch
from shared.tenancy.context import get_current_tenant

from .domain_events import (
    LowStockDetected,
    StockAdjusted,
    StockConsumed,
    StockReceived,
    StockTransferred,
)


def _publish(event: DomainEvent) -> None:
    dispatch(event)


def publish_stock_received(
    *,
    inventory_item_id: uuid.UUID,
    warehouse_id: uuid.UUID | None,
    quantity: Decimal,
    unit_cost: Decimal,
    reference_type: str,
    reference_id: Optional[uuid.UUID],
    reference_number: str = "",
) -> None:
    _publish(StockReceived(
        tenant_id=get_current_tenant(),
        inventory_item_id=inventory_item_id,
        warehouse_id=warehouse_id,
        quantity=str(quantity),
        unit_cost=str(unit_cost),
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
    ))


def publish_stock_consumed(
    *,
    inventory_item_id: uuid.UUID,
    quantity: Decimal,
    reference_type: str,
    reference_id: Optional[uuid.UUID],
) -> None:
    _publish(StockConsumed(
        tenant_id=get_current_tenant(),
        inventory_item_id=inventory_item_id,
        quantity=str(quantity),
        reference_type=reference_type,
        reference_id=reference_id,
    ))


def publish_stock_transferred(
    *,
    transfer_id: uuid.UUID,
    transfer_number: str,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
) -> None:
    _publish(StockTransferred(
        tenant_id=get_current_tenant(),
        transfer_id=transfer_id,
        transfer_number=transfer_number,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
    ))


def publish_stock_adjusted(
    *, adjustment_id: uuid.UUID, adjustment_number: str, reason: str
) -> None:
    _publish(StockAdjusted(
        tenant_id=get_current_tenant(),
        adjustment_id=adjustment_id,
        adjustment_number=adjustment_number,
        reason=reason,
    ))


def publish_low_stock_detected(
    *,
    inventory_item_id: uuid.UUID,
    warehouse_id: uuid.UUID | None,
    product_sku: str,
    quantity_on_hand: Decimal,
    minimum_stock: Decimal,
    out_of_stock: bool,
) -> None:
    _publish(LowStockDetected(
        tenant_id=get_current_tenant(),
        inventory_item_id=inventory_item_id,
        warehouse_id=warehouse_id,
        product_sku=product_sku,
        quantity_on_hand=str(quantity_on_hand),
        minimum_stock=str(minimum_stock),
        out_of_stock=out_of_stock,
    ))
