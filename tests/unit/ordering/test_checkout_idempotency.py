"""Unit tests for checkout idempotency and duplicate transaction prevention."""
import uuid
import pytest
from decimal import Decimal
from django.urls import reverse
from django.core.cache import cache

from contexts.ordering.models import Order, Invoice, Payment, PrintJob
from contexts.ordering.domain.enums import OrderStatus, OrderType, PaymentMethod
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def idempotency_test_data(db, active_tenant):
    set_current_tenant(active_tenant.id)
    
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-IDEM-100",
        status=OrderStatus.OPEN,
        type=OrderType.DINE_IN,
        customer_name="Idempotency Tester",
        subtotal=Decimal("150.00"),
        total=Decimal("150.00"),
    )
    
    # Add an item to make the cart valid
    from contexts.catalog.models.product import Product
    from contexts.catalog.models.category import Category
    cat = Category.objects.create(tenant=active_tenant, name="Test Cat")
    prod = Product.objects.create(tenant=active_tenant, category=cat, name="Test Item", base_price=Decimal("150.00"))
    
    order.items.create(
        tenant=active_tenant,
        product_id=prod.id,
        name_snapshot=prod.name,
        qty=1,
        unit_price=prod.base_price,
        line_subtotal=prod.base_price,
        line_total=prod.base_price
    )

    from unittest.mock import patch
    patcher = patch('contexts.identity.permissions.mixins.TenantPermissionRequiredMixin.has_permission', return_value=True)
    patcher.start()

    yield order
    
    patcher.stop()
    clear_current_tenant()


@pytest.mark.django_db
def test_checkout_modal_injects_idempotency_key(client, admin_user, active_tenant, idempotency_test_data):
    order = idempotency_test_data
    client.force_login(admin_user)
    
    # Setup session
    session = client.session
    session['active_order_id'] = str(order.id)
    session.save()

    url = reverse('ordering:pos_checkout_modal')
    response = client.get(url, HTTP_X_TENANT_ID=str(active_tenant.id))
    
    assert response.status_code == 200
    assert b'name="idempotency_key"' in response.content
    assert b'value=' in response.content


@pytest.mark.django_db
def test_process_payment_idempotency_cache_block(client, admin_user, active_tenant, idempotency_test_data):
    order = idempotency_test_data
    client.force_login(admin_user)
    
    session = client.session
    session['active_order_id'] = str(order.id)
    session.save()

    idempotency_key = "test-idem-12345"
    cache_key = f"checkout_idempotency_{idempotency_key}"
    
    # Seed the cache to simulate a request already in progress
    cache.set(cache_key, "PROCESSING", timeout=60)
    
    url = reverse('ordering:pos_process_payment')
    response = client.post(url, {
        'idempotency_key': idempotency_key,
        'method': 'CASH',
        'tendered': '150.00'
    }, HTTP_X_TENANT_ID=str(active_tenant.id))

    # Should return HTTP 429 Too Many Requests
    assert response.status_code == 429
    assert b"Duplicate request detected" in response.content
    
    # Order should remain OPEN
    order.refresh_from_db()
    assert order.status == OrderStatus.OPEN
    assert Invoice.objects.filter(order=order).count() == 0


@pytest.mark.django_db
def test_process_payment_idempotency_success(client, admin_user, active_tenant, idempotency_test_data):
    order = idempotency_test_data
    client.force_login(admin_user)
    
    session = client.session
    session['active_order_id'] = str(order.id)
    session.save()

    # Clear cache just in case
    cache.clear()
    idempotency_key = "test-idem-success-123"

    url = reverse('ordering:pos_process_payment')
    response = client.post(url, {
        'idempotency_key': idempotency_key,
        'method': 'CASH',
        'tendered': '150.00'
    }, HTTP_X_TENANT_ID=str(active_tenant.id))

    assert response.status_code == 200
    
    from shared.tenancy import set_current_tenant
    set_current_tenant(active_tenant.id)
    
    order.refresh_from_db()
    assert order.status == OrderStatus.SETTLED
    assert Invoice.objects.filter(order=order).count() == 1
    assert Payment.objects.filter(order=order).count() == 1
