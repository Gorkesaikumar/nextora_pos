"""Handlers for inventory events.

Handlers run asynchronously (shared Celery dispatch) and receive the event
**payload dict**, not the dataclass — they must be idempotent (at-least-once
delivery). Registered by importing this module from ``InventoryConfig.ready``.

The per-(tenant, warehouse) stock-availability cache is read on the POS hot path
and must be evicted on any stock change. LowStockDetected is the subscription
point the reorder engine / notifications will hook into.
"""
import logging

from django.core.cache import cache

from shared.infrastructure.events.registry import register_handler

logger = logging.getLogger("nextora.inventory.events")

_AVAILABILITY_CACHE_KEY = "inventory:availability:{tenant_id}:{warehouse_id}"


def invalidate_availability(tenant_id: str | None, warehouse_id: str | None) -> None:
    if tenant_id and warehouse_id:
        cache.delete(_AVAILABILITY_CACHE_KEY.format(
            tenant_id=tenant_id, warehouse_id=warehouse_id
        ))


@register_handler("StockReceived")
def on_stock_received(payload: dict) -> None:
    invalidate_availability(payload.get("tenant_id"), payload.get("warehouse_id"))


@register_handler("StockConsumed")
def on_stock_consumed(payload: dict) -> None:
    # Consumption doesn't carry a warehouse on the event; a coarse log is enough
    # here — the availability cache is keyed per warehouse and evicted on receipt
    # / adjustment, and reconciliation is the safety net.
    logger.info("inventory.stock.consumed", extra={"event": payload})


@register_handler("StockTransferred")
def on_stock_transferred(payload: dict) -> None:
    tenant_id = payload.get("tenant_id")
    invalidate_availability(tenant_id, payload.get("from_warehouse_id"))
    invalidate_availability(tenant_id, payload.get("to_warehouse_id"))


@register_handler("StockAdjusted")
def on_stock_adjusted(payload: dict) -> None:
    logger.info("inventory.stock.adjusted", extra={"event": payload})
    adjustment_id = payload.get("adjustment_id")
    tenant_id = payload.get("tenant_id")
    if adjustment_id and tenant_id:
        from contexts.inventory.models.adjustment import StockAdjustment
        try:
            adjustment = StockAdjustment.all_objects.get(id=adjustment_id)
            invalidate_availability(tenant_id, str(adjustment.warehouse_id))
        except StockAdjustment.DoesNotExist:
            logger.warning(f"StockAdjustment {adjustment_id} not found in handler.")


@register_handler("LowStockDetected")
def on_low_stock_detected(payload: dict) -> None:
    # Subscription point for the reorder engine and notifications context.
    logger.warning(
        "inventory.low_stock",
        extra={
            "product_sku": payload.get("product_sku"),
            "on_hand": payload.get("quantity_on_hand"),
            "minimum": payload.get("minimum_stock"),
            "out_of_stock": payload.get("out_of_stock"),
        },
    )
