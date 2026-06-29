"""POS billing screen (web/HTMX) rendering & wiring.

Covers the redesigned screen: the grid renders real prices (regression for the
``product.price`` → ``base_price`` bug where cards showed a bare "₹"), the
category ribbon endpoint, the stat-card context, and that the core cart
endpoints still return the swappable #pos-cart-panel.
"""
import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from contexts.catalog.models import Category, Product

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
    category = Category.objects.create(name="Biryani", slug="biryani-pos-test")
    return Product.objects.create(
        category=category,
        name="Chicken Biryani",
        sku="CHI-BIR-POS",
        base_price=Decimal("250.00"),
    )


def _host(tenant):
    return f"{tenant.slug}.nextora.app"


def test_pos_main_renders_with_price_and_panels(client, active_tenant, cashier, product):
    client.force_login(cashier)
    response = client.get(reverse("ordering:pos_main"), HTTP_HOST=_host(active_tenant))
    assert response.status_code == 200
    body = response.content.decode()

    # Core regions present.
    assert 'id="pos-cart-panel"' in body
    assert 'id="pos-grid"' in body
    assert 'id="pos-category-ribbon"' in body

    # Price actually renders (the old template used {{ product.price }} which
    # is empty, leaving a bare "₹").
    assert "₹250.00" in body
    assert ">₹</" not in body

    # Stat cards wired from context.
    for ctx_key in (
        "stat_total_items",
        "stat_categories",
        "stat_active_orders",
        "stat_open_kots",
    ):
        assert ctx_key in response.context
    assert response.context["stat_total_items"] == 1


def test_product_grid_partial_filters_and_prices(client, active_tenant, cashier, product):
    client.force_login(cashier)
    url = reverse("ordering:pos_product_grid")

    hit = client.get(url, {"q": "biryani"}, HTTP_HOST=_host(active_tenant))
    assert hit.status_code == 200
    assert "₹250.00" in hit.content.decode()

    miss = client.get(url, {"q": "zzz-nope"}, HTTP_HOST=_host(active_tenant))
    assert "No products found" in miss.content.decode()


def test_category_ribbon_endpoint(client, active_tenant, cashier, product):
    client.force_login(cashier)
    response = client.get(
        reverse("ordering:pos_category_ribbon"), HTTP_HOST=_host(active_tenant)
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "All Items" in body
    assert "Biryani" in body


def test_add_to_cart_returns_swappable_panel(client, active_tenant, cashier, product):
    """The product card posts here; the response must be the #pos-cart-panel
    fragment so HTMX can outerHTML-swap it."""
    client.force_login(cashier)
    response = client.post(
        reverse("ordering:pos_add_to_cart", kwargs={"product_id": product.id}),
        HTTP_HOST=_host(active_tenant),
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="pos-cart-panel"' in body
    assert "Chicken Biryani" in body
    assert "each" in body  # per-unit price line
