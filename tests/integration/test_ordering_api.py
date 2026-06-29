import pytest
import uuid
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from contexts.catalog.models import Category, Product
from contexts.identity.models import Membership, Role, Permission, RolePermission
from contexts.ordering.models import Order

User = get_user_model()
pytestmark = pytest.mark.django_db


def _make_cashier_user(active_tenant, seeded, location_id):
    """Creates a user + role with all ordering permissions needed for the POS flow."""
    user = User.objects.create_user(
        email="cashier@nextora.app",
        full_name="Alice Cashier",
        password="password123"
    )
    role = Role.objects.create(
        tenant=active_tenant,
        code="test_cashier",
        name="Test Cashier"
    )
    for code in [
        "orders.view", "orders.create", "orders.update",
        "orders.void", "orders.discount",
        "payments.capture", "payments.refund",
    ]:
        perm = Permission.objects.get(code=code)
        RolePermission.objects.create(role=role, permission=perm)

    Membership.objects.create(
        tenant=active_tenant,
        user=user,
        role=role,
        location_id=location_id,
        is_active=True
    )
    return user


def test_order_create(active_tenant, seeded):
    location_id = uuid.uuid4()
    user = _make_cashier_user(active_tenant, seeded, location_id)

    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults["HTTP_X_TENANT_ID"] = str(active_tenant.id)
    client.defaults["HTTP_X_BRANCH_ID"] = str(location_id)

    response = client.post("/api/v1/ordering/orders/", {
        "location_id": str(location_id),
        "type": "dine_in",
        "service_charge_rate": "5.00",
    }, format="json")

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["status"] == "open"
    assert Decimal(response.data["service_charge_rate"]) == Decimal("5.00")


def test_order_add_item_and_pay(active_tenant, seeded):
    location_id = uuid.uuid4()
    user = _make_cashier_user(active_tenant, seeded, location_id)

    category = Category.objects.create(
        tenant=active_tenant,
        name="Starters",
        slug="starters-api-test"
    )
    product = Product.objects.create(
        tenant=active_tenant,
        category=category,
        name="Paneer Tikka",
        sku="PNRTK-1-API",
        base_price=Decimal("200.00")
    )

    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults["HTTP_X_TENANT_ID"] = str(active_tenant.id)
    client.defaults["HTTP_X_BRANCH_ID"] = str(location_id)

    # Create order
    r = client.post("/api/v1/ordering/orders/", {
        "location_id": str(location_id),
        "type": "dine_in",
    }, format="json")
    assert r.status_code == status.HTTP_201_CREATED, r.data
    order_id = r.data["id"]

    # Add item
    r = client.post(f"/api/v1/ordering/orders/{order_id}/add_item/", {
        "product_id": str(product.id),
        "qty": 2,
    }, format="json")
    assert r.status_code == status.HTTP_200_OK, r.data
    assert len(r.data["items"]) == 1
    assert r.data["items"][0]["name_snapshot"] == "Paneer Tikka"

    total = r.data["total"]

    # Pay
    r = client.post(f"/api/v1/ordering/orders/{order_id}/pay/", {
        "amount": total,
        "method": "cash",
        "tendered": total,
        "idempotency_key": "idem-pay-api-test-1",
    }, format="json")
    assert r.status_code == status.HTTP_201_CREATED, r.data
    assert r.data["method"] == "cash"
    assert r.data["status"] == "captured"


def test_order_void(active_tenant, seeded):
    from contexts.ordering.services.order_service import create_order

    location_id = uuid.uuid4()
    user = _make_cashier_user(active_tenant, seeded, location_id)

    order = create_order(location_id=location_id, order_type="takeaway")

    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults["HTTP_X_TENANT_ID"] = str(active_tenant.id)
    client.defaults["HTTP_X_BRANCH_ID"] = str(location_id)

    r = client.post(f"/api/v1/ordering/orders/{order.id}/void/", {
        "reason": "customer_cancelled"
    }, format="json")
    assert r.status_code == status.HTTP_200_OK, r.data
    assert r.data["status"] == "void"


