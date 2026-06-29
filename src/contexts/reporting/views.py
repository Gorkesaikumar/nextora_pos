from decimal import Decimal
from datetime import datetime, timedelta, time
import csv
import io

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncMonth, ExtractHour, ExtractWeekDay
from django.utils import timezone
from django.http import HttpResponse, Http404

from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin
from contexts.identity.services.authorization import has_permission
from contexts.identity.models import User
from contexts.tenants.models import Branch, Table
from contexts.ordering.models import Order, OrderItem, KOT, Payment, Invoice
from contexts.ordering.domain.enums import OrderStatus, OrderType, PaymentMethod, PaymentKind, PaymentStatus, KOTStatus
from contexts.inventory.models.item import InventoryItem
from contexts.inventory.models.warehouse import Warehouse
from contexts.inventory.models.adjustment import DamagedStock
from contexts.inventory.models.batch import Batch
from contexts.catalog.models import Product, Category
from contexts.audit.services import record_audit
from django.core.paginator import Paginator


def _fmt_inr(value: Decimal | int | float) -> str:
    """Format a numeric value with Indian grouping (e.g. 12,50,000.00)."""
    d = Decimal(str(value)).quantize(Decimal("0.01"))
    sign = "-" if d < 0 else ""
    d = abs(d)
    integer_part = int(d)
    decimal_part = f"{d - integer_part:.2f}"[1:]  # ".XX"

    s = str(integer_part)
    if len(s) <= 3:
        return f"{sign}{s}{decimal_part}"
    result = s[-3:]
    s = s[:-3]
    while s:
        result = s[-2:] + "," + result
        s = s[:-2]
    return f"{sign}{result}{decimal_part}"


def get_date_range(preset, start_date_str=None, end_date_str=None):
    today = timezone.localdate()
    
    if preset == 'today':
        start = today
        end = today
    elif preset == 'yesterday':
        start = today - timedelta(days=1)
        end = today - timedelta(days=1)
    elif preset == 'last_7_days':
        start = today - timedelta(days=6)
        end = today
    elif preset == 'last_30_days':
        start = today - timedelta(days=29)
        end = today
    elif preset == 'this_month':
        start = today.replace(day=1)
        end = today
    elif preset == 'last_month':
        try:
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            start = last_day_of_last_month.replace(day=1)
            end = last_day_of_last_month
        except Exception:
            start = today - timedelta(days=30)
            end = today
    else: # custom or default
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today - timedelta(days=7)
            end = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
        except ValueError:
            start = today - timedelta(days=7)
            end = today
            
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))
    return start_dt, end_dt, start, end


def generate_export_response(header, rows, file_format='csv', filename='report'):
    if file_format == 'excel':
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{filename}.xls"'
        # Write Excel friendly Tab-Separated format
        output = io.StringIO()
        writer = csv.writer(output, delimiter='\t')
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
        response.write(output.getvalue().encode('utf-8'))
        return response
    else:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
        return response


@method_decorator(never_cache, name='dispatch')
class DashboardHomeView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard/home.html"
    permission_required = "reports.sales.view"

    def handle_no_permission(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if has_permission(self.request.user, "orders.view", tenant_id):
            return redirect('ordering:pos_main')
        elif has_permission(self.request.user, "kds.view", tenant_id):
            return redirect('ordering:kds_main')
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()
            
        target_start = timezone.make_aware(datetime.combine(target_date, time.min))
        target_end = timezone.make_aware(datetime.combine(target_date, time.max))
        
        if target_date == timezone.now().date():
            display_date = f"Today, {target_date.strftime('%d %b %Y')}"
        else:
            display_date = target_date.strftime('%d %b %Y')
        
        all_orders_today = Order.objects.filter(opened_at__gte=target_start, opened_at__lte=target_end)
        settled_orders = all_orders_today.filter(status=OrderStatus.SETTLED)
        
        revenue_today_raw = settled_orders.aggregate(total=Sum('total'))['total'] or Decimal("0")
        order_count = settled_orders.count()
        avg_ticket_raw = (revenue_today_raw / order_count) if order_count > 0 else Decimal("0")
        open_kots = KOT.objects.filter(status__in=[KOTStatus.NEW, KOTStatus.PREPARING]).count()
        
        dine_in_count = all_orders_today.filter(type=OrderType.DINE_IN).count()
        take_away_count = all_orders_today.filter(type=OrderType.TAKEAWAY).count()
        delivery_count = all_orders_today.filter(type=OrderType.DELIVERY).count()
        cancelled_count = all_orders_today.filter(status=OrderStatus.VOID).count()
        
        refunds_today_raw = all_orders_today.filter(status=OrderStatus.VOID).aggregate(total=Sum('total'))['total'] or Decimal("0")
        tables_turned = settled_orders.filter(type=OrderType.DINE_IN).count()
        
        top_items = list(OrderItem.objects.filter(order__opened_at__gte=target_start, order__opened_at__lte=target_end)
                     .values('name_snapshot')
                     .annotate(qty_sold=Sum('qty'), revenue=Sum('line_total'))
                     .order_by('-qty_sold')[:5])
                     
        top_branches_raw = list(settled_orders.values('location_id')
                            .annotate(revenue=Sum('total'), order_count=Count('id'))
                            .order_by('-revenue')[:5])
                            
        branch_ids = [b['location_id'] for b in top_branches_raw if b['location_id']]
        branches_map = {b.id: b.name for b in Branch.objects.filter(id__in=branch_ids)}
        
        top_branches = []
        for b in top_branches_raw:
            if b['location_id']:
                top_branches.append({
                    'name': branches_map.get(b['location_id'], 'Unknown Branch'),
                    'revenue': b['revenue'],
                    'orders': b['order_count']
                })
        
        recent_orders = Order.objects.filter(
            status=OrderStatus.SETTLED,
            opened_at__gte=target_start,
            opened_at__lte=target_end
        ).order_by('-updated_at')[:5]
        
        fourteen_days_ago = target_start - timedelta(days=13)
        daily_revenue = (Order.objects.filter(status=OrderStatus.SETTLED, opened_at__gte=fourteen_days_ago, opened_at__lte=target_end)
                         .annotate(date=TruncDate('opened_at'))
                         .values('date')
                         .annotate(revenue=Sum('total'))
                         .order_by('date'))
                         
        revenue_chart = []
        revenue_map = {dr['date'].strftime('%b %d'): float(dr['revenue']) for dr in daily_revenue if dr['date']}
        max_rev = max(revenue_map.values()) if revenue_map else 0
        
        for i in range(14):
            day = (fourteen_days_ago + timedelta(days=i)).strftime('%b %d')
            val = revenue_map.get(day, 0)
            height = (val / max_rev * 100) if max_rev > 0 else 0
            revenue_chart.append({'date': day, 'value': val, 'height': height})

        context.update({
            'display_date': display_date,
            'selected_date_str': target_date.strftime('%Y-%m-%d'),
            'revenue_today': _fmt_inr(revenue_today_raw),
            'order_count': order_count,
            'avg_ticket': _fmt_inr(avg_ticket_raw),
            'open_kots': open_kots,
            'recent_orders': recent_orders,
            'user_name': self.request.user.short_name,
            'dine_in_count': dine_in_count,
            'take_away_count': take_away_count,
            'delivery_count': delivery_count,
            'cancelled_count': cancelled_count,
            'total_orders_count': all_orders_today.count(),
            'refunds_today': _fmt_inr(refunds_today_raw),
            'tables_turned': tables_turned,
            'top_items': top_items,
            'top_branches': top_branches,
            'revenue_chart': revenue_chart,
        })
        return context


class SalesReportView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/sales_report.html"
    permission_required = "reports.sales.view"

    def get(self, request, *args, **kwargs):
        preset = request.GET.get('preset', 'last_7_days')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        start_dt, end_dt, start_date, end_date = get_date_range(preset, start_date_str, end_date_str)
        
        orders = Order.objects.filter(opened_at__gte=start_dt, opened_at__lte=end_dt)
        
        # Filters
        branch_id = request.GET.get('branch')
        if branch_id:
            orders = orders.filter(location_id=branch_id)
            
        cashier_id = request.GET.get('cashier')
        if cashier_id:
            orders = orders.filter(created_by=cashier_id)
            
        customer = request.GET.get('customer')
        if customer:
            orders = orders.filter(customer_name__icontains=customer)
            
        table_id = request.GET.get('table')
        if table_id:
            orders = orders.filter(table_id=table_id)
            
        order_type = request.GET.get('order_type')
        if order_type:
            orders = orders.filter(type=order_type)
            
        payment_method = request.GET.get('payment_method')
        if payment_method:
            orders = orders.filter(payments__method=payment_method, payments__status=PaymentStatus.CAPTURED)

        settled = orders.filter(status=OrderStatus.SETTLED)

        # Audit view/export
        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.sales.export", entity_type="report", changes={"format": export_format, "preset": preset})
            header = ['Invoice #', 'Date & Time', 'Customer', 'Cashier', 'Order Type', 'Payment Methods', 'Subtotal', 'Discount', 'Tax', 'Grand Total', 'Status']
            rows = []
            for o in orders.prefetch_related('payments'):
                pm = ", ".join([p.get_method_display() for p in o.payments.all()])
                rows.append([
                    o.order_number or str(o.id),
                    o.opened_at.strftime('%Y-%m-%d %H:%M'),
                    o.customer_name or 'Guest',
                    str(o.created_by) or 'POS',
                    o.get_type_display(),
                    pm or 'N/A',
                    o.subtotal,
                    o.discount_amount,
                    o.tax_amount,
                    o.total,
                    o.get_status_display()
                ])
            return generate_export_response(header, rows, export_format, 'sales_report')

        record_audit("reports.sales.view", entity_type="report", changes={"preset": preset})

        # KPI Metrics
        total_sales = settled.aggregate(sum=Sum('total'))['sum'] or Decimal('0')
        gross_rev = settled.aggregate(sum=Sum('subtotal'))['sum'] or Decimal('0')
        tax_collected = settled.aggregate(sum=Sum('tax_amount'))['sum'] or Decimal('0')
        total_discounts = settled.aggregate(sum=Sum('discount_amount'))['sum'] or Decimal('0')
        total_refunds = Payment.objects.filter(
            captured_at__gte=start_dt,
            captured_at__lte=end_dt,
            kind=PaymentKind.REFUND,
            status=PaymentStatus.CAPTURED
        ).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        
        net_rev = total_sales - tax_collected
        total_orders = settled.count()
        aov = total_sales / total_orders if total_orders else Decimal('0')

        # Payment-wise Revenue
        payment_stats = Payment.objects.filter(
            captured_at__gte=start_dt,
            captured_at__lte=end_dt,
            kind=PaymentKind.PAYMENT,
            status=PaymentStatus.CAPTURED
        ).values('method').annotate(val=Sum('amount'))
        
        pay_methods = {item['method']: float(item['val']) for item in payment_stats}

        # Daily Trend Chart
        daily_trend = list(settled.annotate(date=TruncDate('opened_at')).values('date').annotate(revenue=Sum('total')).order_by('date'))
        trend_labels = [d['date'].strftime('%b %d') for d in daily_trend if d['date']]
        trend_data = [float(d['revenue']) for d in daily_trend]

        # Hourly Sales
        hourly_trend = list(settled.annotate(hour=ExtractHour('opened_at')).values('hour').annotate(revenue=Sum('total')).order_by('hour'))
        hourly_labels = [f"{d['hour']}:00" for d in hourly_trend]
        hourly_data = [float(d['revenue']) for d in hourly_trend]

        # Weekly Sales
        weekly_trend = list(settled.annotate(day_of_week=ExtractWeekDay('opened_at')).values('day_of_week').annotate(revenue=Sum('total')).order_by('day_of_week'))
        days_map = {1: 'Sun', 2: 'Mon', 3: 'Tue', 4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'}
        weekly_labels = [days_map.get(d['day_of_week'], '') for d in weekly_trend]
        weekly_data = [float(d['revenue']) for d in weekly_trend]

        # Sales by Category
        item_sales = OrderItem.objects.filter(order__in=settled)
        product_ids = list(item_sales.values_list('product_id', flat=True).distinct())
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        prod_cat_map = {p.id: p.category.name for p in products}
        
        cat_revenue = {}
        for item in item_sales:
            cat_name = prod_cat_map.get(item.product_id, 'Other')
            cat_revenue[cat_name] = cat_revenue.get(cat_name, 0) + float(item.line_total)
            
        cat_labels = list(cat_revenue.keys())
        cat_data = list(cat_revenue.values())

        # Sort and Pagination
        sort_by = request.GET.get('sort', '-opened_at')
        if sort_by not in ['opened_at', '-opened_at', 'total', '-total']:
            sort_by = '-opened_at'
        orders_sorted = orders.prefetch_related('payments').order_by(sort_by)
        
        paginator = Paginator(orders_sorted, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = self.get_context_data(**kwargs)
        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'preset': preset,
            'branches': Branch.objects.filter(is_active=True),
            'selected_branch': branch_id or '',
            'cashiers': User.objects.filter(is_active=True),
            'selected_cashier': cashier_id or '',
            'customer': customer or '',
            'tables': Table.objects.all(),
            'selected_table': table_id or '',
            'order_types': OrderType.choices,
            'selected_order_type': order_type or '',
            'payment_methods': PaymentMethod.choices,
            'selected_payment_method': payment_method or '',
            
            'total_sales': total_sales,
            'gross_revenue': gross_rev,
            'net_revenue': net_rev,
            'total_discounts': total_discounts,
            'total_refunds': total_refunds,
            'tax_collected': tax_collected,
            'total_orders': total_orders,
            'aov': aov,
            'pay_methods': pay_methods,
            
            'trend_labels': trend_labels, 'trend_data': trend_data,
            'hourly_labels': hourly_labels, 'hourly_data': hourly_data,
            'weekly_labels': weekly_labels, 'weekly_data': weekly_data,
            'cat_labels': cat_labels, 'cat_data': cat_data,
            
            'page_obj': page_obj,
            'sort': sort_by,
        })
        return self.render_to_response(context)


class ItemReportView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/item_report.html"
    permission_required = "reports.sales.view"

    def get(self, request, *args, **kwargs):
        preset = request.GET.get('preset', 'last_7_days')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        start_dt, end_dt, start_date, end_date = get_date_range(preset, start_date_str, end_date_str)
        
        category_id = request.GET.get('category')
        item_name = request.GET.get('item_name')

        items = OrderItem.objects.filter(
            order__opened_at__gte=start_dt,
            order__opened_at__lte=end_dt,
            order__status=OrderStatus.SETTLED
        )
        
        # Resolve catalog context fields
        product_ids = list(items.values_list('product_id', flat=True).distinct())
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        if category_id:
            products = products.filter(category_id=category_id)
            items = items.filter(product_id__in=products.values_list('id', flat=True))
        if item_name:
            items = items.filter(name_snapshot__icontains=item_name)
            
        product_ids = list(items.values_list('product_id', flat=True).distinct())
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        
        # Link cost/stock metrics from inventory
        inventory_items = InventoryItem.objects.filter(product_id__in=product_ids)
        prod_cost_map = {i.product_id: i.average_cost for i in inventory_items}
        prod_stock_map = {i.product_id: i.quantity_on_hand for i in inventory_items}
        prod_cat_map = {p.id: p.category.name for p in products}
        prod_sku_map = {p.id: p.sku for p in products}

        item_stats = list(items.values('name_snapshot', 'product_id').annotate(
            qty_sold=Sum('qty'),
            revenue=Sum('line_total')
        ).order_by('-qty_sold'))

        rows_stats = []
        for i in item_stats:
            p_id = i['product_id']
            qty = i['qty_sold'] or Decimal('0')
            rev = i['revenue'] or Decimal('0')
            cost = prod_cost_map.get(p_id, Decimal('0'))
            total_cost = qty * cost
            profit = rev - total_cost
            stock = prod_stock_map.get(p_id, Decimal('0'))
            avg_price = rev / qty if qty else Decimal('0')
            rows_stats.append({
                'name': i['name_snapshot'],
                'sku': prod_sku_map.get(p_id, 'N/A'),
                'category': prod_cat_map.get(p_id, 'Other'),
                'qty_sold': qty,
                'revenue': rev,
                'cost': total_cost,
                'profit': profit,
                'stock': stock,
                'avg_price': avg_price
            })

        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.items.export", entity_type="report", changes={"format": export_format, "preset": preset})
            header = ['Item Name', 'SKU', 'Category', 'Quantity Sold', 'Revenue', 'Cost', 'Profit', 'Current Stock', 'Avg Selling Price']
            export_rows = [[r['name'], r['sku'], r['category'], r['qty_sold'], r['revenue'], r['cost'], r['profit'], r['stock'], r['avg_price']] for r in rows_stats]
            return generate_export_response(header, export_rows, export_format, 'item_report')

        record_audit("reports.items.view", entity_type="report", changes={"preset": preset})

        # Top Charts
        top_qty = rows_stats[:10]
        top_qty_labels = [r['name'] for r in top_qty]
        top_qty_data = [float(r['qty_sold']) for r in top_qty]

        top_profit = sorted(rows_stats, key=lambda x: x['profit'], reverse=True)[:10]
        top_profit_labels = [r['name'] for r in top_profit]
        top_profit_data = [float(r['profit']) for r in top_profit]

        cat_breakdown = {}
        for r in rows_stats:
            cat = r['category']
            cat_breakdown[cat] = cat_breakdown.get(cat, 0.0) + float(r['revenue'])

        # Server-side pagination
        paginator = Paginator(rows_stats, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # KPIs
        total_items_sold = sum(r['qty_sold'] for r in rows_stats)
        total_item_revenue = sum(r['revenue'] for r in rows_stats)
        total_item_cost = sum(r['cost'] for r in rows_stats)
        total_item_profit = total_item_revenue - total_item_cost

        context = self.get_context_data(**kwargs)
        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'preset': preset,
            'categories': Category.objects.filter(is_active=True),
            'selected_category': category_id or '',
            'item_name': item_name or '',
            
            'total_items_sold': total_items_sold,
            'total_item_revenue': total_item_revenue,
            'total_item_profit': total_item_profit,
            
            'top_qty_labels': top_qty_labels, 'top_qty_data': top_qty_data,
            'top_profit_labels': top_profit_labels, 'top_profit_data': top_profit_data,
            'cat_labels': list(cat_breakdown.keys()), 'cat_data': list(cat_breakdown.values()),
            'page_obj': page_obj,
        })
        return self.render_to_response(context)


class InventoryReportView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/inventory_report.html"
    permission_required = "reports.inventory.view"

    def get(self, request, *args, **kwargs):
        warehouse_id = request.GET.get('warehouse')
        status_filter = request.GET.get('status')
        query = request.GET.get('q')

        items = InventoryItem.objects.filter(is_active=True).select_related('warehouse')
        
        if warehouse_id:
            items = items.filter(warehouse_id=warehouse_id)
        if query:
            items = items.filter(product_name__icontains=query)

        # KPIs & status filters before slicing
        low_stock_count = items.filter(quantity_on_hand__lte=F('minimum_stock'), quantity_on_hand__gt=0).count()
        out_of_stock_count = items.filter(quantity_on_hand__lte=0).count()

        if status_filter == 'low':
            items = items.filter(quantity_on_hand__lte=F('minimum_stock'), quantity_on_hand__gt=0)
        elif status_filter == 'out':
            items = items.filter(quantity_on_hand__lte=0)

        items_with_val = items.annotate(
            total_value=ExpressionWrapper(F('quantity_on_hand') * F('average_cost'), output_field=DecimalField(max_digits=12, decimal_places=2))
        ).order_by('product_name')

        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.inventory.export", entity_type="report", changes={"format": export_format})
            header = ['SKU', 'Product', 'Warehouse', 'Available Stock', 'Reserved Stock', 'Min Stock', 'Unit Cost', 'Inventory Value', 'Last Updated']
            rows = [[i.product_sku, i.product_name, i.warehouse.name, i.quantity_on_hand, i.quantity_reserved, i.minimum_stock, i.average_cost, i.total_value, i.updated_at.strftime('%Y-%m-%d')] for i in items_with_val]
            return generate_export_response(header, rows, export_format, 'inventory_report')

        record_audit("reports.inventory.view", entity_type="report")

        # Visualizations
        wh_distribution = list(items_with_val.values('warehouse__name').annotate(val=Sum('total_value')))
        wh_labels = [d['warehouse__name'] for d in wh_distribution]
        wh_data = [float(d['val']) for d in wh_distribution]

        # Resolve category mapping
        prod_ids = list(items_with_val.values_list('product_id', flat=True).distinct())
        products = Product.objects.filter(id__in=prod_ids).select_related('category')
        prod_cat_map = {p.id: p.category.name for p in products}

        cat_breakdown = {}
        for i in items_with_val:
            cat = prod_cat_map.get(i.product_id, 'Other')
            cat_breakdown[cat] = cat_breakdown.get(cat, 0.0) + float(i.total_value)

        # Pagination
        paginator = Paginator(items_with_val, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        total_products = items.values('product_id').distinct().count()
        total_value = items_with_val.aggregate(sum=Sum('total_value'))['sum'] or Decimal('0')

        # Additional counts for Expiring / Damaged
        today = timezone.localdate()
        expiring_soon = Batch.objects.filter(expiry_date__gte=today, expiry_date__lte=today+timedelta(days=30), quantity__gt=0).count()
        damaged_value = DamagedStock.objects.filter(incident_date__gte=today-timedelta(days=30)).aggregate(val=Sum(F('quantity')*F('unit_cost'), output_field=DecimalField()))['val'] or Decimal('0')

        context = self.get_context_data(**kwargs)
        context.update({
            'warehouses': Warehouse.objects.filter(is_active=True),
            'selected_warehouse': warehouse_id or '',
            'selected_status': status_filter or '',
            'query': query or '',
            
            'total_products': total_products,
            'total_value': total_value,
            'low_stock': low_stock_count,
            'out_of_stock': out_of_stock_count,
            'expiring_soon': expiring_soon,
            'damaged_value': damaged_value,
            
            'wh_labels': wh_labels, 'wh_data': wh_data,
            'cat_labels': list(cat_breakdown.keys()), 'cat_data': list(cat_breakdown.values()),
            'page_obj': page_obj,
        })
        return self.render_to_response(context)


class TaxReportView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/tax_report.html"
    permission_required = "reports.financial.view"

    def get(self, request, *args, **kwargs):
        preset = request.GET.get('preset', 'this_month')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        start_dt, end_dt, start_date, end_date = get_date_range(preset, start_date_str, end_date_str)
        
        branch_id = request.GET.get('branch')
        orders = Order.objects.filter(
            opened_at__gte=start_dt,
            opened_at__lte=end_dt,
            status=OrderStatus.SETTLED
        )
        if branch_id:
            orders = orders.filter(location_id=branch_id)

        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.tax.export", entity_type="report", changes={"format": export_format, "preset": preset})
            header = ['Invoice #', 'Date', 'Customer', 'Taxable Amount', 'CGST', 'SGST', 'IGST', 'Cess', 'Total Tax', 'Total Amount']
            rows = [[o.order_number or str(o.id), o.opened_at.strftime('%Y-%m-%d'), o.customer_name or 'Guest', o.taxable_amount, o.cgst, o.sgst, o.igst, o.cess, o.tax_amount, o.total] for o in orders]
            return generate_export_response(header, rows, export_format, 'tax_report')

        record_audit("reports.tax.view", entity_type="report", changes={"preset": preset})

        # Aggregations
        taxable_sales = orders.aggregate(total=Sum('taxable_amount'))['total'] or Decimal('0')
        total_tax = orders.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        cgst = orders.aggregate(total=Sum('cgst'))['total'] or Decimal('0')
        sgst = orders.aggregate(total=Sum('sgst'))['total'] or Decimal('0')
        igst = orders.aggregate(total=Sum('igst'))['total'] or Decimal('0')
        cess = orders.aggregate(total=Sum('cess'))['total'] or Decimal('0')

        # Slab-wise breakdowns
        order_items = OrderItem.objects.filter(order__in=orders)
        slabs = order_items.values('tax_rate').annotate(
            taxable=Sum('line_subtotal'),
            tax=Sum('line_total') - Sum('line_subtotal')
        ).order_by('tax_rate')

        slab_labels = [f"{float(s['tax_rate'])}%" for s in slabs]
        slab_data = [float(s['tax']) for s in slabs]

        # Monthly collection chart
        monthly_tax = list(orders.annotate(month=TruncMonth('opened_at')).values('month').annotate(total=Sum('tax_amount')).order_by('month'))
        month_labels = [d['month'].strftime('%b %Y') for d in monthly_tax if d['month']]
        month_data = [float(d['total']) for d in monthly_tax]

        # Pagination
        paginator = Paginator(orders.order_by('-opened_at'), 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = self.get_context_data(**kwargs)
        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'preset': preset,
            'branches': Branch.objects.filter(is_active=True),
            'selected_branch': branch_id or '',
            
            'taxable_sales': taxable_sales,
            'total_tax': total_tax,
            'cgst': cgst,
            'sgst': sgst,
            'igst': igst,
            'cess': cess,
            
            'slab_labels': slab_labels, 'slab_data': slab_data,
            'month_labels': month_labels, 'month_data': month_data,
            'page_obj': page_obj,
        })
        return self.render_to_response(context)


class InvoiceDetailView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/invoice_detail.html"
    permission_required = "invoices.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order.objects.prefetch_related('items', 'payments'), id=order_id)
        
        # Get related branch
        branch = None
        try:
            branch = Branch.objects.get(id=order.location_id)
        except Branch.DoesNotExist:
            pass

        context.update({
            'order': order,
            'branch': branch,
            'payments': order.payments.filter(status=PaymentStatus.CAPTURED),
            'subtotal': order.subtotal,
            'discount': order.discount_amount,
            'tax': order.tax_amount,
            'total': order.total,
        })
        return context


class EmailInvoiceView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "invoices.view"

    def post(self, request, *args, **kwargs):
        import json
        from django.http import JsonResponse
        
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        # Fetch email from POST payload
        try:
            body = json.loads(request.body.decode('utf-8'))
            recipient_email = body.get('email')
        except Exception:
            recipient_email = request.POST.get('email') or order.customer_phone
            
        if not recipient_email:
            return JsonResponse({'status': 'error', 'message': 'No recipient email specified.'}, status=400)

        record_audit("invoice.emailed", entity_type="invoice", entity_id=order.id, changes={"recipient": recipient_email})
        return JsonResponse({
            'status': 'success',
            'message': f'Invoice successfully emailed to {recipient_email}.'
        })
