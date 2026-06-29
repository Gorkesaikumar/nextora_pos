"""Tests for catalog domain events (transactional outbox + handlers)."""
from decimal import Decimal

import pytest
from django.core.cache import cache

from contexts.catalog.events import handlers
from contexts.catalog.models import Category, Product
from contexts.catalog.services import product_service
from shared.infrastructure.events.models import OutboxEvent
from shared.infrastructure.events.registry import get_handlers

pytestmark = pytest.mark.django_db


def _category(name="Food"):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    return Category.objects.create(name=f"{name}-{suffix}", slug=f"{name.lower()}-{suffix}")


def _outbox(event_type):
    return OutboxEvent.objects.filter(event_type=event_type)


# --- Publishing to the outbox ---------------------------------------------
def test_create_product_publishes_event(active_tenant):
    product = product_service.create_product(
        {"category": _category(), "name": "Burger", "sku": "BUR1",
         "base_price": Decimal("150.00")}
    )
    event = _outbox("ProductCreated").get()
    assert event.payload["sku"] == "BUR1"
    assert event.payload["product_id"] == str(product.id)
    assert event.tenant_id == active_tenant.id


def test_price_change_emits_dedicated_event(active_tenant):
    product = product_service.create_product(
        {"category": _category(), "name": "Tea", "sku": "TEA1",
         "base_price": Decimal("10.00")}
    )
    product_service.update_product(product.id, {"base_price": Decimal("12.00")})

    assert _outbox("ProductUpdated").exists()
    price_event = _outbox("ProductPriceChanged").get()
    assert price_event.payload["old_price"] == "10.00"
    assert price_event.payload["new_price"] == "12.00"


def test_update_without_price_change_emits_no_price_event(active_tenant):
    product = product_service.create_product(
        {"category": _category(), "name": "Tea", "sku": "TEA2",
         "base_price": Decimal("10.00")}
    )
    product_service.update_product(product.id, {"name": "Green Tea"})
    assert not _outbox("ProductPriceChanged").exists()


def test_delete_product_publishes_event(active_tenant):
    product = product_service.create_product(
        {"category": _category(), "name": "Soda", "sku": "SODA1",
         "base_price": Decimal("20.00")}
    )
    product_service.delete_product(product.id)
    event = _outbox("ProductDeleted").get()
    assert event.payload["sku"] == "SODA1"


# --- Handler registration & behaviour -------------------------------------
def test_handlers_are_registered():
    for name in ("ProductCreated", "ProductUpdated",
                 "ProductPriceChanged", "ProductDeleted"):
        assert get_handlers(name), f"no handler registered for {name}"


def test_handler_invalidates_menu_cache():
    tenant_id = "11111111-1111-1111-1111-111111111111"
    key = handlers._MENU_CACHE_KEY.format(tenant_id=tenant_id)
    cache.set(key, {"stale": True})
    handlers.on_product_price_changed({"tenant_id": tenant_id})
    assert cache.get(key) is None
