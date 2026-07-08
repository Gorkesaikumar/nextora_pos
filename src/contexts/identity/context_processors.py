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
        if tenant_id:
            try:
                return reverse(f"{viewname}_tenant", kwargs={'tenant_id': tenant_id})
            except NoReverseMatch:
                pass
                
            try:
                return reverse(viewname, kwargs={'tenant_id': tenant_id})
            except NoReverseMatch:
                pass

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
            'active': request.path.startswith('/pos/') and '/kds/' not in request.path and '/tables/' not in request.path and '/print-queue/' not in request.path,
        })
    if 'branches.view' in perms:
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('ordering:pos_tables_main'),
            'icon': 'armchair',
            'active': request.path.startswith('/pos/') and '/tables/' in request.path,
        })
    if 'kds.view' in perms:
        operations_items.append({
            'label': 'KOT / Kitchen',
            'url': safe_reverse('ordering:kds_main'),
            'icon': 'chef-hat',
            'active': request.path.startswith('/pos/') and '/kds/' in request.path,
        })
    if 'orders.view' in perms:
        operations_items.append({
            'label': 'Print Queue',
            'url': safe_reverse('ordering:print_queue'),
            'icon': 'printer',
            'active': request.path.startswith('/pos/') and '/print-queue/' in request.path,
        })
    if 'catalog.view' in perms:
        operations_items.append({
            'label': 'Menu Items',
            'url': safe_reverse('catalog:product_list'),
            'icon': 'utensils-crossed',
            'active': '/dashboard/catalog/' in request.path and '/products' in request.path,
        })
        operations_items.append({
            'label': 'Modifiers',
            'url': safe_reverse('catalog:modifier_group_list'),
            'icon': 'list-plus',
            'active': '/dashboard/catalog/' in request.path and '/modifiers' in request.path,
        })
        operations_items.append({
            'label': 'Combo Offers',
            'url': safe_reverse('catalog:combo_list'),
            'icon': 'tags',
            'active': '/dashboard/catalog/' in request.path and '/combos/' in request.path,
        })
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('restaurant:table_list'),
            'icon': 'grid',
            'active': '/dashboard/restaurant/' in request.path and ('/tables/' in request.path or '/floors/' in request.path),
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
                'active': '/inventory/' in request.path and ('/items/' in request.path or request.path.endswith('/inventory/')),
            },
            {
                'label': 'Purchase',
                'url': safe_reverse('inventory:purchase_list'),
                'icon': 'shopping-cart',
                'active': '/inventory/' in request.path and '/purchases/' in request.path,
            },
            {
                'label': 'Suppliers',
                'url': safe_reverse('inventory:supplier_list'),
                'icon': 'users',
                'active': '/inventory/' in request.path and '/suppliers/' in request.path,
            },
            {
                'label': 'Stock Adjustments',
                'url': safe_reverse('inventory:adjustment_list'),
                'icon': 'sliders-horizontal',
                'active': '/inventory/' in request.path and '/adjustments/' in request.path,
            },
        ])
    if inventory_items:
        nav_groups.append({'label': 'INVENTORY', 'items': inventory_items})

    # CUSTOMERS
    customer_items = []
    if 'customers.view' in perms:
        customer_items.extend([
            {'label': 'Customers', 'url': '#', 'icon': 'users-2', 'active': '/customers/' in request.path},
            {'label': 'Loyalty & Offers', 'url': '#', 'icon': 'heart-handshake', 'active': '/loyalty/' in request.path},
        ])
    if customer_items:
        nav_groups.append({'label': 'CUSTOMERS', 'items': customer_items})

    # BILLING
    billing_items = []
    if 'orders.view' in perms or 'reports.sales.view' in perms:
        billing_items.extend([
            {'label': 'Billing Dashboard', 'url': safe_reverse('billing:dashboard'), 'icon': 'layout-dashboard', 'active': '/dashboard/' in request.path and '/billing/' in request.path},
            {'label': 'Invoices', 'url': safe_reverse('billing:invoices'), 'icon': 'file-text', 'active': '/invoices/' in request.path},
            {'label': 'Billing Reports', 'url': safe_reverse('billing:reports'), 'icon': 'pie-chart', 'active': '/reports/' in request.path and '/billing/' in request.path},
            {'label': 'Payment History', 'url': safe_reverse('billing:payments'), 'icon': 'history', 'active': '/payments/' in request.path},
            {'label': 'GST Reports', 'url': safe_reverse('billing:gst_reports'), 'icon': 'calculator', 'active': '/gst-reports/' in request.path},
            {'label': 'GST Filing', 'url': safe_reverse('billing:gst_filing'), 'icon': 'file-check', 'active': '/gst-filing/' in request.path},
            {'label': 'Tax Summary', 'url': safe_reverse('billing:tax_summary'), 'icon': 'landmark', 'active': '/tax-summary/' in request.path},
            {'label': 'Refund Bills', 'url': safe_reverse('billing:refunds'), 'icon': 'undo', 'active': '/refunds/' in request.path},
            {'label': 'WhatsApp Sharing', 'url': safe_reverse('billing:whatsapp'), 'icon': 'message-circle', 'active': '/whatsapp/' in request.path},
            {'label': 'Activity History', 'url': safe_reverse('billing:audit_log'), 'icon': 'shield-check', 'active': '/audit/' in request.path},
            {'label': 'Billing Settings', 'url': safe_reverse('billing:settings'), 'icon': 'settings', 'active': '/settings/' in request.path and '/billing/' in request.path},

        ])
    if billing_items:
        nav_groups.append({'label': 'BILLING', 'items': billing_items})

    # REPORTS
    report_items = []
    if 'reports.sales.view' in perms:
        report_items.extend([
            {'label': 'Sales Report', 'url': safe_reverse('reporting:sales'), 'icon': 'bar-chart-3', 'active': '/reports/sales/' in request.path},
            {'label': 'Item Report', 'url': safe_reverse('reporting:items'), 'icon': 'pie-chart', 'active': '/reports/items/' in request.path},
            {'label': 'Modifier Analytics', 'url': safe_reverse('catalog:modifier_analytics'), 'icon': 'list-tree', 'active': '/modifiers/analytics/' in request.path},
            {'label': 'Inventory Report', 'url': safe_reverse('reporting:inventory'), 'icon': 'clipboard-list', 'active': '/reports/inventory/' in request.path},
            {'label': 'Tax Report', 'url': safe_reverse('reporting:tax'), 'icon': 'file-text', 'active': '/reports/tax/' in request.path},
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
            'active': '/dashboard/restaurant/' in request.path and '/branches/' in request.path,
        })
    if 'users.view' in perms:
        settings_items.append({
            'label': 'Users',
            'url': safe_reverse('employees:employee_list'),
            'icon': 'user-cog',
            'active': '/dashboard/staff/' in request.path and '/directory/' in request.path,
        })
        settings_items.extend([
            {
                'label': 'Roles & Permissions',
                'url': safe_reverse('employees:role_list'),
                'icon': 'shield-check',
                'active': '/dashboard/staff/' in request.path and '/roles/' in request.path
            },
            {
                'label': 'Printers',
                'url': safe_reverse('restaurant:printer_list'),
                'icon': 'printer',
                'active': '/dashboard/restaurant/' in request.path and '/printers/' in request.path
            },
        ])
    
    if settings_items:
        nav_groups.append({'label': 'SETTINGS', 'items': settings_items})

    return {
        'user_permissions': perms,
        'nav_groups': nav_groups,
    }
