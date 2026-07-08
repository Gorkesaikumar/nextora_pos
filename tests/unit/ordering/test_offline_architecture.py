"""Unit tests for Nextora POS Enterprise Offline Architecture & Sync APIs."""
from decimal import Decimal
import uuid
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from contexts.catalog.models import Category, Product, TaxClass
from contexts.identity.models import User
from contexts.ordering.models import Order
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    u = User.objects.create(
        email=f"cashier-{uuid.uuid4().hex[:6]}@acme.com",
        is_active=True,
    )
    u.set_password("SecurePass123!")
    u.save()
    return u


@pytest.fixture
def catalog_data(db, active_tenant):
    cat = Category.objects.create(tenant=active_tenant, name="Beverages", sort_order=1)
    tax = TaxClass.objects.create(tenant=active_tenant, name="GST 5%", gst_rate=Decimal("5.00"))
    prod = Product.objects.create(
        tenant=active_tenant,
        category=cat,
        sku="BEV-001",
        name="Artisanal Espresso",
        base_price=Decimal("150.00"),
        tax_class=tax,
        is_active=True,
    )
    return {"category": cat, "tax": tax, "product": prod}


@pytest.mark.django_db
def test_offline_bootstrap_api(api_client, user, active_tenant, catalog_data):
    api_client.force_authenticate(user=user)
    set_current_tenant(active_tenant.id)
    try:
        url = reverse("offline_bootstrap")
        response = api_client.get(url, HTTP_X_TENANT_ID=str(active_tenant.id))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "version" in data
        assert "products" in data
        assert "categories" in data
        assert "user_permissions" in data
        assert any(p["sku"] == "BEV-001" for p in data["products"])
    finally:
        clear_current_tenant()


@pytest.mark.django_db
def test_offline_sync_idempotent_ingestion(api_client, user, active_tenant, catalog_data):
    api_client.force_authenticate(user=user)
    set_current_tenant(active_tenant.id)
    try:
        url = reverse("offline_sync")

        offline_ord_id = f"OFF-ORD-{uuid.uuid4().hex[:8]}"
        idempotency_key = f"IDEM-{uuid.uuid4().hex}"

        sync_payload = {
            "transactions": [
                {
                    "idempotency_key": idempotency_key,
                    "payload": {
                        "offline_reference_id": offline_ord_id,
                        "location_id": str(uuid.uuid4()),
                        "subtotal": "150.00",
                        "tax_total": "7.50",
                        "grand_total": "157.50",
                        "items": [
                            {
                                "product_id": str(catalog_data["product"].id),
                                "name": "Artisanal Espresso",
                                "quantity": 1,
                                "unit_price": "150.00"
                            }
                        ],
                        "payments": [
                            {"method": "cash", "amount": "157.50"}
                        ]
                    }
                }
            ]
        }

        # 1. First sync attempt should succeed and create order
        response1 = api_client.post(url, sync_payload, format="json", HTTP_X_TENANT_ID=str(active_tenant.id))
        set_current_tenant(active_tenant.id)
        assert response1.status_code == status.HTTP_200_OK
        res_data1 = response1.json()
        assert res_data1["results"][0]["status"] == "SUCCESS", res_data1["results"][0]
        assert res_data1["synced_count"] == 1

        # Verify order exists in DB
        order = Order.objects.get(offline_reference_id=offline_ord_id)
        assert order.total == Decimal("157.50")

        # 2. Duplicate sync attempt should detect duplicate and skip creation
        response2 = api_client.post(url, sync_payload, format="json", HTTP_X_TENANT_ID=str(active_tenant.id))
        set_current_tenant(active_tenant.id)
        assert response2.status_code == status.HTTP_200_OK
        res_data2 = response2.json()
        assert res_data2["results"][0]["status"] == "DUPLICATE_SKIPPED"
        assert res_data2["results"][0]["order_id"] == str(order.id)

        # Ensure no duplicate order record was created
        assert Order.objects.filter(offline_reference_id=offline_ord_id).count() == 1
    finally:
        clear_current_tenant()
