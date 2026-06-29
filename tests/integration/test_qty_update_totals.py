"""Regression: changing an order-item quantity must recompute line totals.

Adding a ₹250 product then incrementing to qty 3 must yield line_total=750 and
order.subtotal=750, not the stale qty=1 value of 250.
"""
import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from contexts.catalog.models import Category, Product
from contexts.ordering.domain.enums import ItemStatus, OrderStatus
from contexts.ordering.models import Order, OrderItem
from contexts.ordering.services import order_service
from shared.tenancy import tenant_context

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def allow_all_hosts(settings):
    settings.ALLOWED_HOSTS = ["*"]
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.fixture
def cashier(tenant, make_user, system_role):
    from contexts.identity.models import Membership

    user = make_user()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("company_owner"), is_active=True
    )
    return user


@pytest.fixture
def product(active_tenant):
    category = Category.objects.create(name="Biryani", slug="biryani-qty-test")
    return Product.objects.create(
        category=category,
        name="Chicken Biryani",
        sku="CHI-BIR-QTY",
        base_price=Decimal("250.00"),
    )


def _host(tenant):
    return f"{tenant.slug}.nextora.app"


# ── Service-layer tests ─────────────────────────────────────────────

def test_set_item_qty_recomputes_line_total(active_tenant, product):
    order = order_service.create_order(
        location_id=uuid.uuid4(), order_type="takeaway"
    )
    item = order_service.add_item(order.id, product, qty=Decimal("1"))
    assert item.line_total == Decimal("250.00")

    item = order_service.set_item_qty(order.id, item.id, Decimal("3"))
    assert item.qty == Decimal("3")
    assert item.line_total == Decimal("750.00")

    order.refresh_from_db()
    assert order.subtotal == Decimal("750.00")
    assert order.total >= Decimal("750.00")


def test_set_item_qty_to_zero_voids_item(active_tenant, product):
    order = order_service.create_order(
        location_id=uuid.uuid4(), order_type="takeaway"
    )
    item = order_service.add_item(order.id, product, qty=Decimal("1"))

    item = order_service.set_item_qty(order.id, item.id, Decimal("0"))
    assert item.status == ItemStatus.VOID

    order.refresh_from_db()
    assert order.subtotal == Decimal("0.00")


# ── View-layer tests (HTMX cart endpoints) ──────────────────────────

def test_add_to_cart_twice_increments_qty_and_total(
    client, active_tenant, cashier, product
):
    client.force_login(cashier)
    url = reverse("ordering:pos_add_to_cart", kwargs={"product_id": product.id})
    host = _host(active_tenant)

    client.post(url, HTTP_HOST=host)
    client.post(url, HTTP_HOST=host)
    client.post(url, HTTP_HOST=host)

    order_id = client.session["active_order_id"]
    # Re-enter tenant context — the middleware clears it after each request.
    with tenant_context(active_tenant.id):
        order = Order.objects.get(id=order_id)
        item = order.items.get(status=ItemStatus.ACTIVE)

        assert item.qty == Decimal("3")
        assert item.line_total == Decimal("750.00")
        assert order.subtotal == Decimal("750.00")


def test_update_item_add_recomputes_total(
    client, active_tenant, cashier, product
):
    client.force_login(cashier)
    host = _host(active_tenant)

    client.post(
        reverse("ordering:pos_add_to_cart", kwargs={"product_id": product.id}),
        HTTP_HOST=host,
    )
    order_id = client.session["active_order_id"]
    with tenant_context(active_tenant.id):
        item = OrderItem.objects.get(order_id=order_id, status=ItemStatus.ACTIVE)

    for _ in range(2):
        client.post(
            reverse(
                "ordering:pos_update_item",
                kwargs={"item_id": item.id, "action": "add"},
            ),
            HTTP_HOST=host,
        )

    with tenant_context(active_tenant.id):
        item.refresh_from_db()
        order = Order.objects.get(id=order_id)

        assert item.qty == Decimal("3")
        assert item.line_total == Decimal("750.00")
        assert order.subtotal == Decimal("750.00")


def test_update_item_sub_recomputes_total(
    client, active_tenant, cashier, product
):
    client.force_login(cashier)
    host = _host(active_tenant)

    # Add qty=1, then increment twice to get qty=3
    add_url = reverse("ordering:pos_add_to_cart", kwargs={"product_id": product.id})
    client.post(add_url, HTTP_HOST=host)
    client.post(add_url, HTTP_HOST=host)
    client.post(add_url, HTTP_HOST=host)

    order_id = client.session["active_order_id"]
    with tenant_context(active_tenant.id):
        item = OrderItem.objects.get(order_id=order_id, status=ItemStatus.ACTIVE)
        assert item.qty == Decimal("3")

    # Decrement once -> qty=2
    client.post(
        reverse(
            "ordering:pos_update_item",
            kwargs={"item_id": item.id, "action": "sub"},
        ),
        HTTP_HOST=host,
    )

    with tenant_context(active_tenant.id):
        item.refresh_from_db()
        order = Order.objects.get(id=order_id)

        assert item.qty == Decimal("2")
        assert item.line_total == Decimal("500.00")
        assert order.subtotal == Decimal("500.00")
