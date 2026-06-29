import pytest
from decimal import Decimal
from django.utils import timezone
from contexts.search.services import universal_search
from contexts.catalog.models import Category, Product
from contexts.customers.models import Customer
from contexts.inventory.models.supplier import Supplier
from contexts.ordering.models import Order, Invoice
from contexts.identity.models import Membership, Role
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_universal_search_invoice_and_models(active_tenant):
    # 1. Seed Product & Category
    category = Category.objects.create(
        tenant=active_tenant,
        name="Drinks",
        slug="drinks-test-search"
    )
    product = Product.objects.create(
        tenant=active_tenant,
        category=category,
        name="Mango Shake",
        sku="MNG-SHK-1",
        base_price=Decimal("150.00")
    )

    # 2. Seed Customer
    customer = Customer.objects.create(
        tenant=active_tenant,
        name="Aravind Sharma",
        phone="9876543210",
        email="aravind@example.com"
    )

    # 3. Seed Supplier
    supplier = Supplier.objects.create(
        tenant=active_tenant,
        name="Gourmet Foods Ltd",
        code="GOURMET",
        phone="1122334455",
        email="orders@gourmet.com"
    )

    # 4. Seed Invoice
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=active_tenant.id,
        subtotal=Decimal("150.00"),
        total=Decimal("150.00"),
        due_amount=Decimal("0.00")
    )
    invoice = Invoice.objects.create(
        tenant=active_tenant,
        order=order,
        location_id=order.location_id,
        number="INV-2026-9999",
        financial_year="2026-2027",
        subtotal=Decimal("150.00"),
        total=Decimal("150.00")
    )

    # 5. Seed Employee (Membership + User)
    user = User.objects.create_user(
        email="waiter@nextora.app",
        full_name="Rajesh Kumar",
        password="password123"
    )
    role = Role.objects.create(
        tenant=active_tenant,
        code="waiter",
        name="Waiter"
    )
    membership = Membership.objects.create(
        tenant=active_tenant,
        user=user,
        role=role,
        is_active=True
    )

    # Test Product search
    res = universal_search("Mango", active_tenant.id, entity_type="products")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "Mango Shake"

    # Test Category search
    res = universal_search("Drinks", active_tenant.id, entity_type="categories")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "Drinks"

    # Test Invoice search (fixes the invoice_number vs number bug)
    res = universal_search("INV-2026", active_tenant.id, entity_type="invoices")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "INV-2026-9999"

    # Test Customer search
    res = universal_search("Aravind", active_tenant.id, entity_type="customers")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "Aravind Sharma"

    # Test Supplier search
    res = universal_search("Gourmet", active_tenant.id, entity_type="suppliers")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "Gourmet Foods Ltd"

    # Test Employee search
    res = universal_search("Rajesh", active_tenant.id, entity_type="employees")
    assert res["count"] > 0
    assert res["results"][0]["title"] == "Rajesh Kumar"

    # Test Universal search ('all' type)
    res_all = universal_search("Mango", active_tenant.id, entity_type="all")
    assert res_all["count"] > 0
    assert any(item["type"] == "product" for item in res_all["results"])


def test_search_cache_invalidation_signals(active_tenant):
    from django.core.cache import cache
    import hashlib

    # Create category first so we can create product
    category = Category.objects.create(
        tenant=active_tenant,
        name="Desserts",
        slug="desserts-search-test"
    )
    product = Product.objects.create(
        tenant=active_tenant,
        category=category,
        name="Chocolate Cake",
        sku="CHOC-CAKE-1",
        base_price=Decimal("120.00")
    )

    # Perform a search to populate cache
    query = "Chocolate"
    res = universal_search(query, active_tenant.id, entity_type="products")
    assert res["count"] > 0

    # Verify cache key is populated
    query_hash = hashlib.md5(query.strip().lower().encode("utf-8")).hexdigest()
    cache_key = f"search:{active_tenant.id}:products:{query_hash}:20:0"
    
    # We should have a cached entry
    assert cache.get(cache_key) is not None

    # Update the Customer model (Customer signals clear search cache)
    customer = Customer.objects.create(
        tenant=active_tenant,
        name="Test Cache Invalidator",
        phone="5555555555"
    )

    # The cache should be cleared by the signal receiver
    assert cache.get(cache_key) is None

