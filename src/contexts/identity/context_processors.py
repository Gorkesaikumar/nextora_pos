from django.urls import reverse, NoReverseMatch

from contexts.identity.services.authorization import get_permission_codes

def rbac_context(request):
    """Injects user permissions and RBAC-filtered navigation items."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'user_permissions': frozenset(), 'nav_items': []}

    tenant_id = getattr(request, 'tenant_id', None)
    location_id = getattr(request, 'branch_id', None)

    perms = get_permission_codes(request.user, tenant_id)

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
    
    resolver = getattr(request, 'resolver_match', None)
    app_name = resolver.app_name if resolver else ''
    url_name = resolver.url_name if resolver else ''
    view_name = resolver.view_name if resolver else ''
    
    # If in Super Admin, override nav groups entirely
    if app_name == 'super_admin' or request.path.startswith('/platform/'):
        super_admin_items = [
            {'label': 'Dashboard', 'url': reverse('super_admin:dashboard'), 'icon': 'layout-dashboard', 'active': request.path == '/platform/'},
            {'label': 'Tenants', 'url': reverse('super_admin:tenant_list'), 'icon': 'building-2', 'active': request.path.startswith('/platform/tenants/')},
            {'label': 'Users & Staff', 'url': reverse('super_admin:user_list'), 'icon': 'users', 'active': request.path.startswith('/platform/users/')},
            {'label': 'Audit Log', 'url': reverse('super_admin:audit_log_list'), 'icon': 'shield-alert', 'active': request.path.startswith('/platform/audit-logs/')},
            {'label': 'SaaS Plans', 'url': reverse('super_admin:plan_list'), 'icon': 'layers', 'active': request.path.startswith('/platform/plans')},
            {'label': 'Free Trials', 'url': reverse('super_admin:trial_config'), 'icon': 'clock', 'active': request.path.startswith('/platform/trials')},
            {'label': 'Feature Visibility', 'url': reverse('super_admin:visibility_config'), 'icon': 'eye', 'active': request.path.startswith('/platform/visibility')},
            {'label': 'SaaS Coupons', 'url': reverse('super_admin:coupon_discount_list'), 'icon': 'tag', 'active': request.path.startswith('/platform/saas-coupons')},
        ]
        return {
            'user_permissions': frozenset(),
            'nav_groups': [{'label': 'ADMINISTRATION', 'items': super_admin_items}],
            'brand_text_main': 'ADMIN PANEL',
            'brand_text_sub': 'NEXTORA CREATIONS',
        }


    # Dashboard (Standalone, no group header)
    if 'reports.sales.view' in perms or 'reports.financial.view' in perms:
        nav_groups.append({
            'label': None,
            'items': [{
                'label': 'Dashboard',
                'url': safe_reverse('reporting:home'),
                'icon': 'layout-dashboard',
                'active': app_name == 'reporting' and url_name in ('home', 'home_tenant'),
            }]
        })

    # OPERATIONS
    operations_items = []
    
    if 'orders.view' in perms or 'orders.create' in perms:
        operations_items.append({
            'label': 'Orders',
            'url': safe_reverse('ordering:pos_main'),
            'icon': 'receipt',
            'active': app_name == 'ordering' and url_name.startswith('pos_') and 'table' not in url_name and 'checkout' not in url_name and 'payment' not in url_name and 'printer' not in url_name,
        })
    if 'branches.view' in perms:
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('ordering:pos_tables_main'),
            'icon': 'armchair',
            'active': app_name == 'ordering' and 'table' in url_name,
        })
    if 'kds.view' in perms:
        operations_items.append({
            'label': 'KOT / Kitchen',
            'url': safe_reverse('ordering:kds_main'),
            'icon': 'chef-hat',
            'active': app_name == 'ordering' and 'kds' in url_name,
        })
    if 'orders.view' in perms:
        operations_items.append({
            'label': 'Print Queue',
            'url': safe_reverse('ordering:print_queue'),
            'icon': 'printer',
            'active': app_name == 'ordering' and 'print_queue' in url_name,
        })
    if 'catalog.view' in perms:
        operations_items.append({
            'label': 'Menu Items',
            'url': safe_reverse('catalog:product_list'),
            'icon': 'utensils-crossed',
            'active': app_name == 'catalog' and 'product' in url_name,
        })
        operations_items.append({
            'label': 'Modifiers',
            'url': safe_reverse('catalog:modifier_group_list'),
            'icon': 'list-plus',
            'active': app_name == 'catalog' and 'modifier' in url_name and 'analytics' not in url_name,
        })
        operations_items.append({
            'label': 'Combo Offers',
            'url': safe_reverse('catalog:combo_list'),
            'icon': 'tags',
            'active': app_name == 'catalog' and 'combo' in url_name,
        })
        operations_items.append({
            'label': 'Tables',
            'url': safe_reverse('restaurant:table_list'),
            'icon': 'layout-grid',
            'active': app_name == 'restaurant' and ('table' in url_name or 'floor' in url_name) and 'printer' not in url_name,
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
                'active': app_name == 'inventory' and 'item' in url_name,
            },
            {
                'label': 'Purchase',
                'url': safe_reverse('inventory:purchase_list'),
                'icon': 'shopping-cart',
                'active': app_name == 'inventory' and 'purchase' in url_name,
            },
            {
                'label': 'Stock Adjustments',
                'url': safe_reverse('inventory:adjustment_list'),
                'icon': 'sliders-horizontal',
                'active': app_name == 'inventory' and 'adjustment' in url_name,
            },
        ])
    if inventory_items:
        nav_groups.append({'label': 'INVENTORY', 'items': inventory_items})

    # CUSTOMERS
    customer_items = []
    if 'customers.view' in perms:
        customer_items.extend([
            {'label': 'Customers', 'url': '#', 'icon': 'users', 'active': app_name == 'customers'},
            {'label': 'Loyalty & Offers', 'url': '#', 'icon': 'heart-handshake', 'active': app_name == 'loyalty'},
        ])
    if customer_items:
        nav_groups.append({'label': 'CUSTOMERS', 'items': customer_items})

    # BILLING
    billing_items = []
    if 'orders.view' in perms or 'reports.sales.view' in perms:
        billing_items.extend([
            {'label': 'Billing Dashboard', 'url': safe_reverse('billing:dashboard'), 'icon': 'layout-dashboard', 'active': app_name == 'billing' and 'dashboard' in url_name},
            {'label': 'Invoices', 'url': safe_reverse('billing:invoices'), 'icon': 'file-text', 'active': app_name == 'billing' and 'invoices' in url_name},
            {'label': 'Billing Reports', 'url': safe_reverse('billing:reports'), 'icon': 'pie-chart', 'active': app_name == 'billing' and 'reports' in url_name},
            {'label': 'Payment History', 'url': safe_reverse('billing:payments'), 'icon': 'history', 'active': app_name == 'billing' and 'payment' in url_name},
            {'label': 'GST Reports', 'url': safe_reverse('billing:gst_reports'), 'icon': 'calculator', 'active': app_name == 'billing' and 'gst' in url_name and 'report' in url_name},
            {'label': 'GST Filing', 'url': safe_reverse('billing:gst_filing'), 'icon': 'file-check', 'active': app_name == 'billing' and 'gst' in url_name and 'filing' in url_name},
            {'label': 'Tax Summary', 'url': safe_reverse('billing:tax_summary'), 'icon': 'landmark', 'active': app_name == 'billing' and 'tax' in url_name},
            {'label': 'Refund Bills', 'url': safe_reverse('billing:refunds'), 'icon': 'undo', 'active': app_name == 'billing' and 'refund' in url_name},
            {'label': 'WhatsApp Sharing', 'url': safe_reverse('billing:whatsapp'), 'icon': 'message-circle', 'active': app_name == 'billing' and 'whatsapp' in url_name},
            {'label': 'Activity History', 'url': safe_reverse('billing:audit_log'), 'icon': 'shield-check', 'active': app_name == 'billing' and 'audit' in url_name},
            {'label': 'Billing Settings', 'url': safe_reverse('billing:settings'), 'icon': 'settings', 'active': app_name == 'billing' and 'setting' in url_name},

        ])
    if billing_items:
        nav_groups.append({'label': 'BILLING', 'items': billing_items})

    # REPORTS
    report_items = []
    if 'reports.sales.view' in perms:
        report_items.extend([
            {'label': 'Sales Report', 'url': safe_reverse('reporting:sales'), 'icon': 'bar-chart', 'active': app_name == 'reporting' and 'sales' in url_name},
            {'label': 'Item Report', 'url': safe_reverse('reporting:items'), 'icon': 'pie-chart', 'active': app_name == 'reporting' and 'item' in url_name},
            {'label': 'Modifier Analytics', 'url': safe_reverse('catalog:modifier_analytics'), 'icon': 'list-tree', 'active': app_name == 'catalog' and 'modifier_analytics' in url_name},
            {'label': 'Inventory Report', 'url': safe_reverse('reporting:inventory'), 'icon': 'clipboard-list', 'active': app_name == 'reporting' and 'inventory' in url_name},
            {'label': 'Tax Report', 'url': safe_reverse('reporting:tax'), 'icon': 'file-text', 'active': app_name == 'reporting' and 'tax' in url_name},
            {'label': 'HR Reports', 'url': safe_reverse('employees:reports'), 'icon': 'briefcase', 'active': app_name == 'employees' and 'report' in url_name},
        ])
    if report_items:
        nav_groups.append({'label': 'REPORTS', 'items': report_items})

    # SETTINGS
    settings_items = []
    if 'users.view' in perms:
        settings_items.append({
            'label': 'Invoice Config',
            'url': safe_reverse('ordering:invoice_config'),
            'icon': 'file-cog',
            'active': app_name == 'ordering' and 'invoice' in url_name,
            'permission': 'orders.update',
        })
        # Check if user has orders.update permission for Invoice Config
        if 'orders.update' not in perms:
            settings_items.pop()
        settings_items.append({
            'label': 'HRMS Dashboard',
            'url': safe_reverse('employees:dashboard'),
            'icon': 'layout-dashboard',
            'active': app_name == 'employees' and 'dashboard' in url_name,
        })
        settings_items.append({
            'label': 'Staff Directory',
            'url': safe_reverse('employees:employee_list'),
            'icon': 'users',
            'active': app_name == 'employees' and 'employee' in url_name,
        })
        settings_items.append({
            'label': 'Staff Documents',
            'url': safe_reverse('employees:document_list'),
            'icon': 'files',
            'active': app_name == 'employees' and 'document' in url_name,
        })
        settings_items.extend([
            {
                'label': 'Departments',
                'url': safe_reverse('employees:department_list'),
                'icon': 'building',
                'active': app_name == 'employees' and 'department' in url_name,
            },
            {
                'label': 'Designations',
                'url': safe_reverse('employees:designation_list'),
                'icon': 'briefcase',
                'active': app_name == 'employees' and 'designation' in url_name,
            },
            {
                'label': 'Shifts & Rules',
                'url': safe_reverse('employees:shift_list'),
                'icon': 'clock',
                'active': app_name == 'employees' and 'shift' in url_name,
            },
            {
                'label': 'Weekly Offs',
                'url': safe_reverse('employees:weeklyoff_list'),
                'icon': 'calendar-off',
                'active': app_name == 'employees' and 'weeklyoff' in url_name,
            },
            {
                'label': 'Attendance Logs',
                'url': safe_reverse('employees:attendance_list'),
                'icon': 'clock',
                'active': app_name == 'employees' and 'attendance' in url_name,
            },
            {
                'label': 'Leave Requests',
                'url': safe_reverse('employees:leave_list'),
                'icon': 'calendar-clock',
                'active': app_name == 'employees' and 'leave' in url_name,
            },
            {
                'label': 'Payroll & Payouts',
                'url': safe_reverse('employees:payroll_list'),
                'icon': 'banknote',
                'active': app_name == 'employees' and 'payroll' in url_name,
            },
            {
                'label': 'Roles & Permissions',
                'url': safe_reverse('employees:role_list'),
                'icon': 'shield-check',
                'active': app_name == 'employees' and 'role' in url_name,
            },
            {
                'label': 'Printers',
                'url': safe_reverse('restaurant:printer_list'),
                'icon': 'printer',
                'active': app_name == 'restaurant' and 'printer' in url_name,
            },
        ])
    
    if settings_items:
        nav_groups.append({'label': 'SETTINGS', 'items': settings_items})

    from contexts.tenants.models import Tenant
    from shared.tenancy.context import bypass_tenant
    tenant = None
    if tenant_id:
        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()

    return {
        'user_permissions': perms,
        'nav_groups': nav_groups,
        'brand_text_main': 'NEXTORA CREATIONS',
        'brand_text_sub': 'POINT OF SALE',
        'tenant': tenant,
    }
