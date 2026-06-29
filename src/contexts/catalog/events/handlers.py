"""Handlers for catalog events.

Handlers run asynchronously (via the shared Celery dispatch) and receive the
event **payload dict**, not the dataclass — they must be idempotent because the
outbox guarantees at-least-once delivery. They are registered by importing this
module, which ``CatalogConfig.ready`` does at startup.

The menu served to POS terminals is cache-heavy and read on every order; any
product change must evict the owning tenant's cached menu so stale prices/items
never reach a bill.
"""
import logging

from django.core.cache import cache

from shared.infrastructure.events.registry import register_handler

logger = logging.getLogger("nextora.catalog.events")

#: Cache key holding the rendered menu for a tenant (built by the menu read side).
_MENU_CACHE_KEY = "catalog:menu:{tenant_id}"


def invalidate_menu_cache(tenant_id: str | None) -> None:
    if tenant_id:
        cache.delete(_MENU_CACHE_KEY.format(tenant_id=tenant_id))


@register_handler("ProductCreated")
def on_product_created(payload: dict) -> None:
    invalidate_menu_cache(payload.get("tenant_id"))
    logger.info("catalog.product.created", extra={"event": payload})


@register_handler("ProductUpdated")
def on_product_updated(payload: dict) -> None:
    invalidate_menu_cache(payload.get("tenant_id"))


@register_handler("ProductPriceChanged")
def on_product_price_changed(payload: dict) -> None:
    invalidate_menu_cache(payload.get("tenant_id"))
    logger.info(
        "catalog.product.price_changed",
        extra={
            "product_id": payload.get("product_id"),
            "old_price": payload.get("old_price"),
            "new_price": payload.get("new_price"),
        },
    )


@register_handler("ProductDeleted")
def on_product_deleted(payload: dict) -> None:
    invalidate_menu_cache(payload.get("tenant_id"))
