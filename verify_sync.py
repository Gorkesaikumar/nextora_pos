import os
import sys
from pathlib import Path
from decimal import Decimal

# Make the `src/` packages importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Set up django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()

from django.test import RequestFactory
from contexts.ordering.services import order_service, kot_service
from contexts.catalog.models import Product, Category
from shared.tenancy.context import set_current_tenant
from contexts.tenants.models import Tenant

from unittest import mock

def run_verification():
    tenant = Tenant.objects.first()
    set_current_tenant(tenant.id)

    # Mock broadcast_tenant_event to catch emitted events
    emitted_events = []

    def mock_broadcast(event_type, *args, **kwargs):
        emitted_events.append(event_type)
        print(f"  [WebSocket Event] Emitted: {event_type}")

    patcher = mock.patch('contexts.ordering.realtime.broadcast_tenant_event', side_effect=mock_broadcast)
    patcher.start()

    print("\n--- Verifying Synchronization Flow ---")
    
    product = Product.objects.first()
    if not product:
        print("No products found in the database. Creating one...")
        cat = Category.objects.first()
        product = Product.objects.create(name="Test Item 123", sku="TEST-SKU-123", base_price=Decimal("10.00"), category=cat)

    # 2. Flutter creates order
    print("\nStep 1: Flutter creates order")
    order = order_service.create_order(order_type='dine_in', created_by=None)
    order_service.add_item(order.id, product, qty=Decimal('1'))
    print(f"  -> Order {order.order_number} created with 1 item.")
    
    # 3. KOT generated
    print("\nStep 2: KOT generated")
    kots = kot_service.generate_kots(order.id)
    print(f"  -> {len(kots)} KOT(s) generated.")
    
    # Trigger on_commit hooks
    from django.db import transaction
    transaction.get_connection().commit()

    from rest_framework.test import APIClient
    client = APIClient()
    # Force authenticate a user (need any user)
    from contexts.identity.models import User
    user = User.objects.first()
    if not user:
        user = User.objects.create_user("testuser", "test@test.com", "password")
    client.force_authenticate(user=user)

    print("\nStep 3: Kitchen marks Preparing")
    response = client.patch(f"/api/v1/ordering/kot/{kots[0].id}/status/", {"status": "preparing"}, format="json")
    print(f"  -> Response: {response.status_code}")
    
    transaction.get_connection().commit()

    print("\nStep 4: Kitchen marks Ready")
    response = client.patch(f"/api/v1/ordering/kot/{kots[0].id}/status/", {"status": "ready"}, format="json")
    print(f"  -> Response: {response.status_code}")
    transaction.get_connection().commit()

    print("\n--- Summary of Fired Events ---")
    print(emitted_events)
    
    patcher.stop()

if __name__ == '__main__':
    run_verification()
