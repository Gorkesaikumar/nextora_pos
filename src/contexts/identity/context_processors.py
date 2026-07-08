from django.urls import reverse, NoReverseMatch

from contexts.identity.services.authorization import get_permission_codes

def rbac_context(request):
    """Injects user permissions and RBAC-filtered navigation items."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'user_permissions': frozenset(), 'nav_items': []}

    tenant_id = getattr(request, 'tenant_id', None)
    location_id = getattr(request, 'branch_id', None)

    perms = get_permission_codes(request.user, tenant_id, location_id)

    def safe_reverse(viewname):
        try:
            return reverse(viewname)
        except NoReverseMatch:
            return '#'

    # Build nav groups based on permissions
    nav_groups = []

    # Dashboard (Standalone, no group header)
    if 'reports.sales.view' in perms or 'reports.financial.view' in perms:
        nav_groups.append({
            'label': None,
            'items': [{
                'label': 'Dashboard',
                'url': '/',
                'icon': 'layout-dashboard',
                'active': request.path == '/',
            }]
        })

    # OPERATIONS
    operations_items = []
    if 'orders.view' in perms or 'orders.create' in perms:
        operations_items.append({
            'label': 'Orders',
            'url': safe_reverse('ordering:pos_main'),
            'icon': 'receipt',
            'active': request.path.startswith('/pos/') and not request.path.startswith('/pos/kds/') and not request.path.startswith('/pos/tables/'),
        })
    if 'branches.view' in perms:
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('ordering:pos_tables_main'),
            'icon': 'armchair',
            'active': request.path.startswith('/pos/tables/'),
        })
    if 'kds.view' in perms:
        operations_items.append({
            'label': 'KOT / Kitchen',
            'url': safe_reverse('ordering:kds_main'),
            'icon': 'chef-hat',
            'active': request.path.startswith('/pos/kds/'),
        })
    if 'orders.view' in perms:
        operations_items.append({
            'label': 'Print Queue',
            'url': safe_reverse('ordering:print_queue'),
            'icon': 'printer',
            'active': request.path.startswith('/pos/print-queue/'),
        })
    if 'catalog.view' in perms:
        operations_items.append({
            'label': 'Menu Items',
            'url': safe_reverse('catalog:product_list'),
            'icon': 'utensils-crossed',
            'active': request.path.startswith('/dashboard/catalog/') and 'products' in request.path,
        })
        operations_items.append({
            'label': 'Modifiers',
            'url': '#', # Placeholder
            'icon': 'list-plus',
            'active': request.path.startswith('/dashboard/modifiers/'),
        })
        operations_items.append({
            'label': 'Combo Offers',
            'url': '#', # Placeholder
            'icon': 'tags',
            'active': request.path.startswith('/dashboard/combos/'),
        })
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('restaurant:table_list'),
            'icon': 'grid',
            'active': request.path.startswith('/dashboard/restaurant/tables/') or request.path.startswith('/dashboard/restaurant/floors/'),
        })
    
    if operations_items:
        nav_groups.append({'label': 'OPERATIONS', 'items': operations_items})

    # INVENTORY
    inventory_items = []
    if 'inventory.view' in perms:
        inventory_items.extend([
            {
                'label': 'Inventory',
                'url': safe_reverse('inventory:item_list'),
                'icon': 'package',
                'active': request.path == '/inventory/' or request.path.startswith('/inventory/items/'),
            },
            {
                'label': 'Purchase',
                'url': safe_reverse('inventory:purchase_list'),
                'icon': 'shopping-cart',
                'active': request.path.startswith('/inventory/purchases/'),
            },
            {
                'label': 'Suppliers',
                'url': safe_reverse('inventory:supplier_list'),
                'icon': 'users',
                'active': request.path.startswith('/inventory/suppliers/'),
            },
            {
                'label': 'Stock Adjustments',
                'url': safe_reverse('inventory:adjustment_list'),
                'icon': 'sliders-horizontal',
                'active': request.path.startswith('/inventory/adjustments/'),
            },
        ])
    if inventory_items:
        nav_groups.append({'label': 'INVENTORY', 'items': inventory_items})

    # CUSTOMERS
    customer_items = []
    if 'customers.view' in perms:
        customer_items.extend([
            {'label': 'Customers', 'url': '#', 'icon': 'users-2', 'active': request.path.startswith('/customers/')},
            {'label': 'Loyalty & Offers', 'url': '#', 'icon': 'heart-handshake', 'active': request.path.startswith('/loyalty/')},
        ])
    if customer_items:
        nav_groups.append({'label': 'CUSTOMERS', 'items': customer_items})

    # BILLING
    billing_items = []
    if 'orders.view' in perms or 'reports.sales.view' in perms:
        billing_items.extend([
            {'label': 'Billing Dashboard', 'url': safe_reverse('billing:dashboard'), 'icon': 'layout-dashboard', 'active': request.path.startswith('/billing/dashboard/')},
            {'label': 'Invoices', 'url': safe_reverse('billing:invoices'), 'icon': 'file-text', 'active': request.path.startswith('/billing/invoices/')},
            {'label': 'Billing Reports', 'url': safe_reverse('billing:reports'), 'icon': 'pie-chart', 'active': request.path.startswith('/billing/reports/')},
            {'label': 'Payment History', 'url': safe_reverse('billing:payments'), 'icon': 'history', 'active': request.path.startswith('/billing/payments/')},
            {'label': 'GST Reports', 'url': safe_reverse('billing:gst_reports'), 'icon': 'calculator', 'active': request.path.startswith('/billing/gst-reports/')},
            {'label': 'GST Filing', 'url': safe_reverse('billing:gst_filing'), 'icon': 'file-check', 'active': request.path.startswith('/billing/gst-filing/')},
            {'label': 'Tax Summary', 'url': safe_reverse('billing:tax_summary'), 'icon': 'landmark', 'active': request.path.startswith('/billing/tax-summary/')},
            {'label': 'Refund Bills', 'url': safe_reverse('billing:refunds'), 'icon': 'undo', 'active': request.path.startswith('/billing/refunds/')},
            {'label': 'WhatsApp Sharing', 'url': safe_reverse('billing:whatsapp'), 'icon': 'message-circle', 'active': request.path.startswith('/billing/whatsapp/')},
            {'label': 'Activity History', 'url': safe_reverse('billing:audit_log'), 'icon': 'shield-check', 'active': request.path.startswith('/billing/audit/')},
            {'label': 'Billing Settings', 'url': safe_reverse('billing:settings'), 'icon': 'settings', 'active': request.path.startswith('/billing/settings/')},

        ])
    if billing_items:
        nav_groups.append({'label': 'BILLING', 'items': billing_items})

    # REPORTS
    report_items = []
    if 'reports.sales.view' in perms:
        report_items.extend([
            {'label': 'Sales Report', 'url': safe_reverse('reporting:sales'), 'icon': 'bar-chart-3', 'active': request.path.startswith('/reports/sales/')},
            {'label': 'Item Report', 'url': safe_reverse('reporting:items'), 'icon': 'pie-chart', 'active': request.path.startswith('/reports/items/')},
            {'label': 'Inventory Report', 'url': safe_reverse('reporting:inventory'), 'icon': 'clipboard-list', 'active': request.path.startswith('/reports/inventory/')},
            {'label': 'Tax Report', 'url': safe_reverse('reporting:tax'), 'icon': 'file-text', 'active': request.path.startswith('/reports/tax/')},
        ])
    if report_items:
        nav_groups.append({'label': 'REPORTS', 'items': report_items})

    # SETTINGS
    settings_items = []
    if 'branches.view' in perms:
        settings_items.append({
            'label': 'Branches',
            'url': safe_reverse('restaurant:branch_list'),
            'icon': 'store',
            'active': request.path.startswith('/dashboard/restaurant/branches/'),
        })
    if 'users.view' in perms:
        settings_items.append({
            'label': 'Users',
            'url': safe_reverse('employees:employee_list'),
            'icon': 'user-cog',
            'active': request.path.startswith('/dashboard/staff/directory/'),
        })
        settings_items.extend([
            {
                'label': 'Roles & Permissions',
                'url': safe_reverse('employees:role_list'),
                'icon': 'shield-check',
                'active': request.path.startswith('/dashboard/staff/roles/')
            },
            {
                'label': 'Printers',
                'url': safe_reverse('restaurant:printer_list'),
                'icon': 'printer',
                'active': request.path.startswith('/dashboard/restaurant/printers/')
            },
        ])
    
    if settings_items:
        nav_groups.append({'label': 'SETTINGS', 'items': settings_items})

    return {
        'user_permissions': perms,
        'nav_groups': nav_groups,
    }
