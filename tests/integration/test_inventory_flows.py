"""End-to-end document flow tests: purchase, transfer, adjustment, damage."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from contexts.audit.models import AuditLog
from contexts.inventory.domain.enums import PurchaseOrderStatus, TransferStatus
from contexts.inventory.models import (
    Batch,
    DamagedStock,
    InventoryItem,
    Supplier,
    Warehouse,
)
from contexts.inventory.models.adjustment import AdjustmentReason
from contexts.inventory.services import (
    approve_and_apply_adjustment,
    create_adjustment,
    create_purchase_order,
    create_transfer,
    dispatch_transfer,
    receive_purchase_order,
    receive_transfer,
    record_damaged_stock,
)
from shared.infrastructure.events.models import OutboxEvent

pytestmark = pytest.mark.django_db


def _warehouse(code="WH1"):
    return Warehouse.objects.create(name="Main", code=code)


def _item(warehouse, *, product_id=None, sku="SKU1", on_hand="0"):
    return InventoryItem.objects.create(
        product_id=product_id or uuid.uuid4(),
        warehouse=warehouse, product_sku=sku, product_name="Item",
        quantity_on_hand=Decimal(on_hand),
    )


def _audited(action):
    return AuditLog.all_objects.filter(action=action).exists()


def _event(event_type):
    return OutboxEvent.objects.filter(event_type=event_type).exists()


# --- Purchase --------------------------------------------------------------
def test_purchase_receipt_increases_stock_audits_and_emits_event(active_tenant):
    wh = _warehouse()
    item = _item(wh, on_hand="0")
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

    item.refresh_from_db()
    po.refresh_from_db()
    assert item.quantity_on_hand == Decimal("100")
    assert item.average_cost == Decimal("5.0000")
    assert po.status == PurchaseOrderStatus.RECEIVED
    assert Batch.objects.filter(inventory_item=item, batch_number="B1").exists()
    assert _audited("purchase_order.received")
    assert _event("StockReceived")


def test_partial_receipt_sets_partially_received(active_tenant):
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
        receipts=[{"line_id": po.lines.first().id, "quantity_received": Decimal("40")}],
    )
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED


# --- Transfer --------------------------------------------------------------
def test_transfer_moves_stock_between_warehouses(active_tenant):
    wh1, wh2 = _warehouse("WH1"), _warehouse("WH2")
    pid = uuid.uuid4()
    src = _item(wh1, product_id=pid, sku="T1", on_hand="50")
    dst = _item(wh2, product_id=pid, sku="T1", on_hand="0")

    transfer = create_transfer(
        tenant_id=active_tenant.id, from_warehouse_id=wh1.id, to_warehouse_id=wh2.id,
        lines=[{"inventory_item_id": src.id, "quantity_requested": Decimal("20")}],
    )
    dispatch_transfer(transfer.id)
    src.refresh_from_db()
    assert src.quantity_on_hand == Decimal("30")  # deducted on dispatch

    receive_transfer(transfer.id)
    dst.refresh_from_db()
    transfer.refresh_from_db()
    assert dst.quantity_on_hand == Decimal("20")
    assert transfer.status == TransferStatus.RECEIVED
    assert _audited("stock_transfer.received")
    assert _event("StockTransferred")


# --- Adjustment ------------------------------------------------------------
def test_adjustment_approval_applies_delta(active_tenant):
    wh = _warehouse()
    item = _item(wh, on_hand="10")
    adj = create_adjustment(
        tenant_id=active_tenant.id, warehouse_id=wh.id,
        reason=AdjustmentReason.PHYSICAL_COUNT,
        lines=[{"inventory_item_id": item.id, "quantity_after": Decimal("8")}],
    )
    approve_and_apply_adjustment(adj.id)
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("8")
    assert _audited("stock_adjustment.approved")
    assert _event("StockAdjusted")


# --- Damage ----------------------------------------------------------------
def test_record_damaged_stock_writes_off_and_records(active_tenant):
    wh = _warehouse()
    item = _item(wh, on_hand="10")
    damaged = record_damaged_stock(
        tenant_id=active_tenant.id, inventory_item_id=item.id, warehouse_id=wh.id,
        quantity=Decimal("3"), damage_reason="Spillage", incident_date=date.today(),
    )
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("7")
    assert damaged.adjustment is not None
    assert DamagedStock.objects.filter(id=damaged.id).exists()
    assert _audited("stock.damaged")
