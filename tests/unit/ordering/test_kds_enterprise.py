"""Unit tests for Nextora POS Enterprise Real-Time KDS Enhancements."""
from decimal import Decimal
import uuid
import pytest
from django.urls import reverse
from django.test import RequestFactory

from contexts.ordering.models import Order, OrderItem, KOT, KOTItem
from contexts.ordering.domain.enums import KOTStatus
from contexts.restaurant.models import Restaurant, Branch, KitchenStation
from contexts.ordering.views import attach_waiters_and_stations_to_kots
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def branch_and_station(db, active_tenant):
    set_current_tenant(active_tenant.id)
    restaurant = Restaurant.objects.create(
        tenant=active_tenant,
        name="Acme Kitchen",
    )
    branch = Branch.objects.create(
        tenant=active_tenant,
        restaurant=restaurant,
        name="Main Branch",
        code="MB001",
        is_active=True,
    )
    station = KitchenStation.objects.create(
        tenant=active_tenant,
        branch=branch,
        code="GRILL",
        name="Grill Station",
        sort_order=10,
        is_active=True,
    )
    yield branch, station
    clear_current_tenant()


@pytest.fixture
def test_kot(db, active_tenant, branch_and_station):
    set_current_tenant(active_tenant.id)
    branch, station = branch_and_station
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=branch.id,
        order_number="ORD-KDS-001",
        status="open",
        subtotal=Decimal("100.00"),
    )
    order_item = OrderItem.objects.create(
        tenant=active_tenant,
        order=order,
        product_id=uuid.uuid4(),
        name_snapshot="Burger",
        unit_price=Decimal("100.00"),
        qty=Decimal("1.00"),
        line_total=Decimal("100.00"),
    )
    kot = KOT.objects.create(
        tenant=active_tenant,
        location_id=branch.id,
        order=order,
        number=101,
        status=KOTStatus.NEW,
        kitchen_station_id=station.id,
    )
    kot_item = KOTItem.objects.create(
        tenant=active_tenant,
        kot=kot,
        order_item=order_item,
        name_snapshot="Burger",
        qty=Decimal("1.00"),
        is_completed=False,
    )
    yield kot, kot_item
    clear_current_tenant()


def test_attach_stations_metadata(db, active_tenant, test_kot):
    set_current_tenant(active_tenant.id)
    kot, _ = test_kot
    enhanced = attach_waiters_and_stations_to_kots([kot])
    assert enhanced[0].station_name == "Grill Station"
    clear_current_tenant()


def test_station_filtering_in_queryset(db, active_tenant, test_kot, branch_and_station):
    set_current_tenant(active_tenant.id)
    kot, _ = test_kot
    _, grill_station = branch_and_station

    # Another station
    salad_station = KitchenStation.objects.create(
        tenant=active_tenant,
        branch=grill_station.branch,
        code="SALAD",
        name="Salad Station",
        sort_order=20,
        is_active=True,
    )
    salad_kot = KOT.objects.create(
        tenant=active_tenant,
        location_id=grill_station.branch.id,
        order=kot.order,
        number=102,
        status=KOTStatus.NEW,
        kitchen_station_id=salad_station.id,
    )

    all_kots = KOT.objects.filter(status__in=[KOTStatus.NEW, KOTStatus.PREPARING])
    assert all_kots.count() == 2

    grill_kots = all_kots.filter(kitchen_station_id=grill_station.id)
    assert grill_kots.count() == 1
    assert grill_kots.first().id == kot.id
    clear_current_tenant()


def test_kot_item_bump_completion_flag(db, active_tenant, test_kot):
    set_current_tenant(active_tenant.id)
    _, kot_item = test_kot
    assert not kot_item.is_completed

    kot_item.is_completed = True
    kot_item.save()
    kot_item.refresh_from_db()
    assert kot_item.is_completed is True
    clear_current_tenant()


def test_kot_status_machine(db, active_tenant, test_kot):
    set_current_tenant(active_tenant.id)
    kot, _ = test_kot
    assert kot.status == KOTStatus.NEW

    kot.status = KOTStatus.PREPARING
    kot.save()
    kot.refresh_from_db()
    assert kot.status == KOTStatus.PREPARING

    kot.status = KOTStatus.READY
    kot.save()
    kot.refresh_from_db()
    assert kot.status == KOTStatus.READY
    clear_current_tenant()
