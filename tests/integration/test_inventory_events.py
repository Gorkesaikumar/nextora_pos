"""Inventory domain-event tests (transactional outbox + handlers)."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from contexts.inventory.domain.enums import AlertStatus, AlertType, StockMovementType
from contexts.inventory.events import handlers  # noqa: F401 (ensures registration)
from contexts.inventory.models import InventoryAlert, InventoryItem, Supplier, Warehouse
from contexts.inventory.services import create_purchase_order, receive_purchase_order
from contexts.inventory.services.movement_service import apply_stock_movement
from shared.infrastructure.events.models import OutboxEvent
from shared.infrastructure.events.registry import get_handlers

pytestmark = pytest.mark.django_db


def _warehouse(code="WH1"):
    return Warehouse.objects.create(name="Main", code=code)


def _item(warehouse, *, on_hand="0", minimum="0"):
    return InventoryItem.objects.create(
        product_id=uuid.uuid4(), warehouse=warehouse,
        product_sku="SKU1", product_name="Item",
        quantity_on_hand=Decimal(on_hand), minimum_stock=Decimal(minimum),
    )


def test_handlers_are_registered():
    for name in ("StockReceived", "StockConsumed", "StockTransferred",
                 "StockAdjusted", "LowStockDetected"):
        assert get_handlers(name), f"no handler registered for {name}"


def test_stock_received_event_payload(active_tenant):
    wh = _warehouse()
    item = _item(wh)
    supplier = Supplier.objects.create(name="Acme")
    po = create_purchase_order(
        tenant_id=active_tenant.id, supplier_id=supplier.id, warehouse_id=wh.id,
        lines=[{"inventory_item_id": item.id, "quantity_ordered": Decimal("100"),
                "unit_cost": Decimal("5")}],
    )
    receive_purchase_order(
        purchase_order_id=po.id,
        receipts=[{"line_id": po.lines.first().id,
                   "quantity_received": Decimal("100"),
                   "batch_number": "B1",
                   "expiry_date": date.today() + timedelta(days=365)}],
    )

    event = OutboxEvent.objects.filter(event_type="StockReceived").latest("created_at")
    assert event.payload["inventory_item_id"] == str(item.id)
    assert event.payload["warehouse_id"] == str(wh.id)
    assert event.payload["quantity"] == "100"
    assert event.tenant_id == active_tenant.id


def test_low_stock_detected_event_and_alert(
    active_tenant, settings, django_capture_on_commit_callbacks
):
    """LowStockDetected fires from the post-commit alert callback."""
    # Run the outbox dispatch inline so the post-commit chain doesn't reach for
    # a Celery broker (none in tests).
    settings.CELERY_TASK_ALWAYS_EAGER = True
    wh = _warehouse()
    item = _item(wh, on_hand="10", minimum="5")

    with django_capture_on_commit_callbacks(execute=True):
        apply_stock_movement(
            inventory_item_id=item.id, movement_type=StockMovementType.SALE,
            quantity=Decimal("-6"),  # 10 → 4, below minimum 5
        )

    assert InventoryAlert.objects.filter(
        inventory_item=item, alert_type=AlertType.LOW_STOCK, status=AlertStatus.OPEN
    ).exists()
    assert OutboxEvent.objects.filter(event_type="LowStockDetected").exists()


def test_no_low_stock_event_when_above_minimum(
    active_tenant, settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    wh = _warehouse()
    item = _item(wh, on_hand="100", minimum="5")
    with django_capture_on_commit_callbacks(execute=True):
        apply_stock_movement(
            inventory_item_id=item.id, movement_type=StockMovementType.SALE,
            quantity=Decimal("-1"),  # 100 → 99, still healthy
        )
    assert not OutboxEvent.objects.filter(event_type="LowStockDetected").exists()


def test_handler_invalidates_availability_cache():
    from django.core.cache import cache

    tenant_id = "11111111-1111-1111-1111-111111111111"
    wh_id = "22222222-2222-2222-2222-222222222222"
    key = handlers._AVAILABILITY_CACHE_KEY.format(tenant_id=tenant_id, warehouse_id=wh_id)
    cache.set(key, {"stale": True})
    handlers.on_stock_received({"tenant_id": tenant_id, "warehouse_id": wh_id})
    assert cache.get(key) is None


def test_stock_adjusted_handler_invalidates_availability_cache(active_tenant):
    from django.core.cache import cache
    from contexts.inventory.models.adjustment import StockAdjustment

    wh = _warehouse()
    adjustment = StockAdjustment.objects.create(
        tenant=active_tenant,
        warehouse=wh,
        adjustment_number="ADJ-1",
        reason="physical_count"
    )

    key = handlers._AVAILABILITY_CACHE_KEY.format(
        tenant_id=str(active_tenant.id), warehouse_id=str(wh.id)
    )
    cache.set(key, {"cached": "data"})
    
    handlers.on_stock_adjusted({"tenant_id": str(active_tenant.id), "adjustment_id": str(adjustment.id)})
    assert cache.get(key) is None
