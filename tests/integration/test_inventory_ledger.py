"""Stock ledger tests: balances, weighted-average cost, idempotency, FEFO."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from contexts.inventory.domain.enums import StockMovementType
from contexts.inventory.exceptions import InsufficientStock
from contexts.inventory.models import Batch, InventoryItem, StockMovement, Warehouse
from contexts.inventory.services.ledger import consume_stock, reconcile_item
from contexts.inventory.services.movement_service import apply_stock_movement

pytestmark = pytest.mark.django_db


def _warehouse(code="WH1", is_default=False):
    return Warehouse.objects.create(name="Main", code=code, is_default=is_default)


def _item(warehouse, *, product_id=None, sku="SKU1", on_hand="0", minimum="0"):
    return InventoryItem.objects.create(
        product_id=product_id or uuid.uuid4(),
        warehouse=warehouse, product_sku=sku, product_name="Item",
        quantity_on_hand=Decimal(on_hand), minimum_stock=Decimal(minimum),
    )


def _in(item, qty, cost, **kw):
    return apply_stock_movement(
        inventory_item_id=item.id, movement_type=StockMovementType.PURCHASE,
        quantity=Decimal(qty), unit_cost=Decimal(cost), **kw,
    )


# --- Balance + weighted-average cost --------------------------------------
def test_stock_in_updates_balance_and_wac(active_tenant):
    item = _item(_warehouse())
    _in(item, "10", "5")
    _in(item, "10", "7")
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("20")
    # (10*5 + 10*7) / 20 = 6
    assert item.average_cost == Decimal("6.0000")


def test_insufficient_stock_raises(active_tenant):
    item = _item(_warehouse(), on_hand="5")
    with pytest.raises(InsufficientStock):
        apply_stock_movement(
            inventory_item_id=item.id, movement_type=StockMovementType.SALE,
            quantity=Decimal("-10"),
        )


def test_allow_negative_permits_below_zero(active_tenant):
    item = _item(_warehouse(), on_hand="5")
    apply_stock_movement(
        inventory_item_id=item.id, movement_type=StockMovementType.SALE,
        quantity=Decimal("-10"), allow_negative=True,
    )
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("-5")


def test_wac_not_corrupted_when_prior_balance_negative(active_tenant):
    """ADR-0001 review A2: stock-in onto a negative balance uses last cost."""
    item = _item(_warehouse(), on_hand="0")
    apply_stock_movement(
        inventory_item_id=item.id, movement_type=StockMovementType.SALE,
        quantity=Decimal("-5"), allow_negative=True,
    )
    _in(item, "10", "8")  # old_balance -5 ≤ 0 → average = last cost
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("5")
    assert item.average_cost == Decimal("8.0000")


# --- Idempotency -----------------------------------------------------------
def test_idempotent_movement_is_applied_once(active_tenant):
    item = _item(_warehouse())
    m1 = _in(item, "10", "5", idempotency_key="recv-1")
    m2 = _in(item, "10", "5", idempotency_key="recv-1")  # redelivery
    assert m1.id == m2.id
    item.refresh_from_db()
    assert item.quantity_on_hand == Decimal("10")  # not 20
    assert StockMovement.objects.filter(inventory_item=item).count() == 1


# --- FEFO consumption ------------------------------------------------------
def test_consume_splits_across_batches_fefo(active_tenant):
    item = _item(_warehouse(), on_hand="30")
    today = date.today()
    batch_soon = Batch.objects.create(
        inventory_item=item, batch_number="SOON",
        expiry_date=today + timedelta(days=5), quantity=Decimal("10"),
    )
    batch_late = Batch.objects.create(
        inventory_item=item, batch_number="LATE",
        expiry_date=today + timedelta(days=90), quantity=Decimal("20"),
    )

    movements = consume_stock(
        inventory_item_id=item.id, quantity=Decimal("15"),
        reference_type="order", reference_id=uuid.uuid4(),
    )

    batch_soon.refresh_from_db()
    batch_late.refresh_from_db()
    item.refresh_from_db()
    assert batch_soon.quantity == Decimal("0")   # earliest expiry drained first
    assert batch_late.quantity == Decimal("15")
    assert item.quantity_on_hand == Decimal("15")
    assert len(movements) == 2


def test_consume_more_than_available_raises(active_tenant):
    item = _item(_warehouse(), on_hand="5")
    with pytest.raises(InsufficientStock):
        consume_stock(inventory_item_id=item.id, quantity=Decimal("10"))


# --- Reconciliation --------------------------------------------------------
def test_reconcile_ok_when_ledger_matches(active_tenant):
    item = _item(_warehouse())
    _in(item, "10", "5")
    report = reconcile_item(item.id)
    assert report["ok"] is True
    assert report["discrepancy"] == Decimal("0")


def test_reconcile_detects_drift(active_tenant):
    item = _item(_warehouse())
    _in(item, "10", "5")
    # Corrupt the projection behind the ledger's back.
    InventoryItem.all_objects.filter(id=item.id).update(quantity_on_hand=Decimal("99"))
    report = reconcile_item(item.id)
    assert report["ok"] is False
    assert report["discrepancy"] == Decimal("89")  # 99 − 10
