from decimal import Decimal
from django.utils import timezone
from datetime import datetime, time
from django.db.models import Sum

from contexts.identity.models import User
from contexts.tenants.models import Tenant
from contexts.catalog.models import Product, KitchenStation, Category
from contexts.ordering.models import Order, KOT, OrderItem
from contexts.ordering.domain.enums import OrderStatus, KOTStatus
from contexts.ordering.services import order_service, kot_service
from shared.tenancy.context import set_current_tenant

def get_dashboard_summary(tenant_id):
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    today_end = timezone.make_aware(datetime.combine(today, time.max))

    orders = Order.objects.filter(tenant_id=tenant_id, opened_at__gte=today_start, opened_at__lte=today_end)
    active_orders = orders.exclude(status=OrderStatus.VOID)

    revenue_today = active_orders.aggregate(sum=Sum('total'))['sum'] or Decimal("0.00")
    orders_today = active_orders.count()
    avg_ticket = (revenue_today / Decimal(orders_today)) if orders_today > 0 else Decimal("0.00")
    open_kots = KOT.objects.filter(order__tenant_id=tenant_id, status__in=[KOTStatus.NEW, KOTStatus.PREPARING]).count()
    
    recent_orders = active_orders.order_by('-updated_at')[:5]

    return {
        "revenue": revenue_today,
        "orders_count": orders_today,
        "avg_ticket": avg_ticket,
        "open_kots": open_kots,
        "recent_orders_count": len(recent_orders),
    }

def verify():
    # Get any valid tenant
    tenant = Tenant.objects.first()
    if not tenant:
        print("ERROR: No tenant found in DB.")
        return
        
    set_current_tenant(tenant.id)
    
    
    
    print(f"--- Verification Started for Tenant {tenant.id} ---")
    
    # 1. Dashboard Initial State
    initial_stats = get_dashboard_summary(tenant.id)
    print(f"Initial State: {initial_stats}")
    
    # Ensure there's a product to add
    product = Product.objects.filter(tenant_id=tenant.id).first()
    if not product:
        # Create a dummy product
        cat = Category.objects.create(tenant=tenant, name="Test Category")
        product = Product.objects.create(tenant=tenant, name="Test Product", base_price=Decimal("150.00"), category=cat)
        print("Created dummy product.")
        
    # 2. Create Walk-in Order
    order = order_service.create_order(
        order_type="takeaway", 
        created_by=None
    )
    print(f"Created Order: {order.order_number} (ID: {order.id})")
    
    # 3. Add Products
    item = order_service.add_item(
        order_id=order.id,
        product=product,
        qty=Decimal("2")
    )
    print(f"Added Item: {item.name_snapshot} x {item.qty} = {item.line_total}")
    
    # 4. Generate KOT
    kots = kot_service.generate_kots(order.id)
    print(f"Generated {len(kots)} KOT(s).")
    
    # 5. Verify Database
    order.refresh_from_db()
    print(f"Order Total in DB: {order.total}")
    
    # 6. Dashboard Final State
    final_stats = get_dashboard_summary(tenant.id)
    print(f"Final State: {final_stats}")
    
    # Assertions
    assert final_stats["orders_count"] == initial_stats["orders_count"] + 1, "Orders count did not increment"
    assert final_stats["revenue"] == initial_stats["revenue"] + order.total, "Revenue did not update correctly"
    assert final_stats["open_kots"] >= initial_stats["open_kots"] + len(kots), "Open KOTs did not update"
    
    print("VERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    verify()
