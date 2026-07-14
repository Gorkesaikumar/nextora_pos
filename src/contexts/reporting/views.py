from decimal import Decimal
from datetime import datetime, date, timedelta, time
import csv
import io

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear, ExtractHour, ExtractWeekDay
from django.utils import timezone
from django.http import HttpResponse, Http404

from shared.tenancy.context import bypass_tenant, get_current_tenant
from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin
from contexts.identity.services.authorization import has_permission
from contexts.identity.models import User
from contexts.tenants.models import Table
from contexts.ordering.models import Order, OrderItem, KOT, Payment, Invoice
from contexts.ordering.domain.enums import OrderStatus, OrderType, PaymentMethod, PaymentKind, PaymentStatus, KOTStatus, InvoiceStatus
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
    if file_format == 'pdf':
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa
        
        html_string = render_to_string('reporting/export_pdf.html', {
            'header': header,
            'rows': rows,
            'title': filename.replace('_', ' ').title()
        })
        
        output = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=output)
        
        if pisa_status.err:
            return HttpResponse('PDF Generation Error', status=500)
            
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response
    elif file_format == 'excel':
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

    def get(self, request, *args, **kwargs):
        if "tenant_id" not in kwargs and getattr(request, "tenant_id", None):
            is_htmx = request.headers.get("HX-Request") == "true"
            if not is_htmx:
                query_string = request.META.get("QUERY_STRING", "")
                url = f"/dashboard/{request.tenant_id}/"
                if query_string:
                    url += f"?{query_string}"
                return redirect(url)
        return super().get(request, *args, **kwargs)

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
                     
        top_branches_raw = list(settled_orders.values('tenant_id')
                            .annotate(revenue=Sum('total'), order_count=Count('id'))
                            .order_by('-revenue')[:5])
                            
        top_branches = []
        for b in top_branches_raw:
            top_branches.append({
                'name': 'Main Branch',
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

class BillingDashboardView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/billing_dashboard.html"
    permission_required = "reports.sales.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        branch_id = self.request.GET.get('branch_id')
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))
        
        orders = Order.objects.all()
        if branch_id:
            orders = orders.filter(location_id=branch_id)
            
        today_orders = orders.filter(opened_at__gte=today_start, opened_at__lte=today_end)
        settled_today = today_orders.filter(status=OrderStatus.SETTLED)
        
        # KPIs
        revenue_today = settled_today.aggregate(sum=Sum('total'))['sum'] or Decimal('0')
        total_bills = settled_today.count()
        avg_bill = (revenue_today / total_bills) if total_bills else Decimal('0')
        gst_collected = settled_today.aggregate(sum=Sum('tax_amount'))['sum'] or Decimal('0')
        
        # Payment Methods
        today_payments = Payment.objects.filter(order__in=today_orders, status=PaymentStatus.CAPTURED, kind=PaymentKind.PAYMENT)
        cash_sales = today_payments.filter(method=PaymentMethod.CASH).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        card_sales = today_payments.filter(method=PaymentMethod.CARD).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        upi_sales = today_payments.filter(method=PaymentMethod.UPI).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        
        # Refunds
        refund_amount = Payment.objects.filter(
            order__in=today_orders, status=PaymentStatus.CAPTURED, kind=PaymentKind.REFUND
        ).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        
        # Pending Payments
        pending_payments = today_orders.exclude(status__in=[OrderStatus.SETTLED, OrderStatus.VOID]).aggregate(sum=Sum('total'))['sum'] or Decimal('0')
        
        # Charts - Daily
        fourteen_days_ago = today_start - timedelta(days=13)
        daily_sales = orders.filter(status=OrderStatus.SETTLED, opened_at__gte=fourteen_days_ago, opened_at__lte=today_end) \
            .annotate(date=TruncDate('opened_at')).values('date').annotate(revenue=Sum('total')).order_by('date')
            
        chart_daily_labels = [d['date'].strftime('%b %d') for d in daily_sales if d['date']]
        chart_daily_data = [float(d['revenue']) for d in daily_sales]
        
        # Hourly
        hourly_sales = settled_today.annotate(hour=ExtractHour('opened_at')).values('hour').annotate(revenue=Sum('total')).order_by('hour')
        chart_hourly_labels = [f"{d['hour']}:00" for d in hourly_sales]
        chart_hourly_data = [float(d['revenue']) for d in hourly_sales]
        
        # Monthly
        six_months_ago = today_start - timedelta(days=180)
        monthly_sales = orders.filter(status=OrderStatus.SETTLED, opened_at__gte=six_months_ago) \
            .annotate(month=TruncMonth('opened_at')).values('month').annotate(revenue=Sum('total')).order_by('month')
        chart_monthly_labels = [d['month'].strftime('%b %Y') for d in monthly_sales if d['month']]
        chart_monthly_data = [float(d['revenue']) for d in monthly_sales]
        
        # Payment pie
        pm_sales = Payment.objects.filter(order__in=orders.filter(status=OrderStatus.SETTLED), status=PaymentStatus.CAPTURED, kind=PaymentKind.PAYMENT) \
            .values('method').annotate(val=Sum('amount'))
        pm_map = {p['method']: float(p['val']) for p in pm_sales}
        chart_pm_labels = ['Card', 'Cash', 'UPI']
        chart_pm_data = [pm_map.get('card', 0), pm_map.get('cash', 0), pm_map.get('upi', 0)]
        
        # GST pie (mocked split based on total GST for now since exact IGST/CGST depends on detailed calculation)
        chart_gst_data = [float(gst_collected * Decimal('0.5')), float(gst_collected * Decimal('0.5')), 0]
        
        context.update({
            'branches': [],
            'selected_branch': '',
            'revenue_today': revenue_today,
            'total_bills': total_bills,
            'avg_bill': avg_bill,
            'gst_collected': gst_collected,
            'cash_sales': cash_sales,
            'card_sales': card_sales,
            'upi_sales': upi_sales,
            'refund_amount': refund_amount,
            'pending_payments': pending_payments,
            'chart_daily_labels': chart_daily_labels,
            'chart_daily_data': chart_daily_data,
            'chart_hourly_labels': chart_hourly_labels,
            'chart_hourly_data': chart_hourly_data,
            'chart_monthly_labels': chart_monthly_labels,
            'chart_monthly_data': chart_monthly_data,
            'chart_pm_labels': chart_pm_labels,
            'chart_pm_data': chart_pm_data,
            'chart_gst_data': chart_gst_data,
            'tenant_id': getattr(self.request, 'tenant_id', None),
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

        export_format = request.GET.get('export')
        report_type = request.GET.get('report_type', 'daily')

        report_headers = []
        report_rows = []

        if report_type == 'daily':
            report_headers = ['Date', 'Orders', 'Gross Sales', 'Discounts', 'Taxes', 'Net Sales']
            daily_data = settled.annotate(date=TruncDate('opened_at')).values('date').annotate(
                order_count=Count('id'), gross=Sum('subtotal'), disc=Sum('discount_amount'),
                tax=Sum('tax_amount'), net=Sum('total')
            ).order_by('-date')
            for d in daily_data:
                report_rows.append([d['date'].strftime('%Y-%m-%d') if d['date'] else 'N/A', d['order_count'], d['gross'], d['disc'], d['tax'], d['net']])
                
        elif report_type == 'cashier':
            report_headers = ['Cashier ID', 'Orders', 'Gross Sales', 'Discounts', 'Taxes', 'Net Sales']
            cashier_data = settled.values('created_by').annotate(
                order_count=Count('id'), gross=Sum('subtotal'), disc=Sum('discount_amount'),
                tax=Sum('tax_amount'), net=Sum('total')
            ).order_by('-net')
            for d in cashier_data:
                report_rows.append([str(d['created_by']) or 'System', d['order_count'], d['gross'], d['disc'], d['tax'], d['net']])
                
        elif report_type == 'branch':
            report_headers = ['Branch ID', 'Orders', 'Gross Sales', 'Discounts', 'Taxes', 'Net Sales']
            branch_data = settled.values('tenant_id').annotate(
                order_count=Count('id'), gross=Sum('subtotal'), disc=Sum('discount_amount'),
                tax=Sum('tax_amount'), net=Sum('total')
            ).order_by('-net')
            for d in branch_data:
                report_rows.append(['Main Branch', d['order_count'], d['gross'], d['disc'], d['tax'], d['net']])
                
        elif report_type == 'payment':
            report_headers = ['Payment Method', 'Transactions', 'Collected Amount']
            payment_data = Payment.objects.filter(
                order__in=settled, kind=PaymentKind.PAYMENT, status=PaymentStatus.CAPTURED
            ).values('method').annotate(count=Count('id'), total=Sum('amount')).order_by('-total')
            for d in payment_data:
                report_rows.append([d['method'], d['count'], d['total']])

        elif report_type == 'customer':
            report_headers = ['Customer Phone', 'Name', 'Orders', 'Total Spent']
            customer_data = settled.exclude(customer_phone="").values('customer_phone', 'customer_name').annotate(
                order_count=Count('id'), total=Sum('total')
            ).order_by('-total')
            for d in customer_data:
                report_rows.append([d['customer_phone'], d['customer_name'] or 'Unknown', d['order_count'], d['total']])
                
        elif report_type == 'refund':
            report_headers = ['Date', 'Refunds Count', 'Total Refunded']
            refund_data = Payment.objects.filter(
                order__in=orders, kind=PaymentKind.REFUND, status=PaymentStatus.CAPTURED
            ).annotate(date=TruncDate('captured_at')).values('date').annotate(
                count=Count('id'), total=Sum('amount')
            ).order_by('-date')
            for d in refund_data:
                report_rows.append([d['date'].strftime('%Y-%m-%d') if d['date'] else 'N/A', d['count'], d['total']])
                
        elif report_type == 'weekly':
            report_headers = ['Week Start', 'Orders', 'Net Sales']
            weekly_data = settled.annotate(week=TruncWeek('opened_at')).values('week').annotate(
                order_count=Count('id'), net=Sum('total')
            ).order_by('-week')
            for d in weekly_data:
                report_rows.append([d['week'].strftime('%Y-%m-%d') if d['week'] else 'N/A', d['order_count'], d['net']])
                
        elif report_type == 'monthly':
            report_headers = ['Month', 'Orders', 'Net Sales']
            monthly_data = settled.annotate(month=TruncMonth('opened_at')).values('month').annotate(
                order_count=Count('id'), net=Sum('total')
            ).order_by('-month')
            for d in monthly_data:
                report_rows.append([d['month'].strftime('%Y-%m') if d['month'] else 'N/A', d['order_count'], d['net']])
                
        elif report_type == 'yearly':
            report_headers = ['Year', 'Orders', 'Net Sales']
            yearly_data = settled.annotate(year=TruncYear('opened_at')).values('year').annotate(
                order_count=Count('id'), net=Sum('total')
            ).order_by('-year')
            for d in yearly_data:
                report_rows.append([d['year'].strftime('%Y') if d['year'] else 'N/A', d['order_count'], d['net']])
                
        elif report_type == 'discount':
            report_headers = ['Discount Type', 'Orders', 'Total Discount']
            discount_data = settled.filter(discount_amount__gt=0).values('discount_type').annotate(
                order_count=Count('id'), total=Sum('discount_amount')
            ).order_by('-total')
            for d in discount_data:
                report_rows.append([d['discount_type'], d['order_count'], d['total']])

        else: # 'invoice'
            report_headers = ['Invoice #', 'Date', 'Customer', 'Cashier', 'Type', 'Subtotal', 'Discount', 'Tax', 'Total', 'Status']
            sort_by = request.GET.get('sort', '-opened_at')
            if sort_by not in ['opened_at', '-opened_at', 'total', '-total']:
                sort_by = '-opened_at'
            
            orders_sorted = orders.prefetch_related('payments').order_by(sort_by)
            
            if export_format:
                for o in orders_sorted:
                    report_rows.append([
                        o.order_number or str(o.id),
                        o.opened_at.strftime('%Y-%m-%d %H:%M'),
                        o.customer_name or 'Guest',
                        str(o.created_by) or 'System',
                        o.get_type_display(),
                        float(o.subtotal),
                        float(o.discount_amount),
                        float(o.tax_amount),
                        float(o.total),
                        o.get_status_display()
                    ])
            else:
                report_rows = orders_sorted # Pass queryset directly for pagination

        # Audit view/export
        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.sales.export", entity_type="report", changes={"format": export_format, "report_type": report_type, "preset": preset})
            return generate_export_response(report_headers, report_rows, export_format, f'{report_type}_report')

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

        # Pagination for dynamic rows
        paginator = Paginator(report_rows, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = self.get_context_data(**kwargs)
        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'preset': preset,
            'branches': [],
            'selected_branch': '',
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
            'report_headers': report_headers,
            'report_type': report_type,
            'sort': request.GET.get('sort', '-opened_at'),
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

        # Aggregations for the filtered period
        taxable_sales = orders.filter(tax_amount__gt=0).aggregate(total=Sum('taxable_amount'))['total'] or Decimal('0')
        total_tax = orders.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        cgst = orders.aggregate(total=Sum('cgst'))['total'] or Decimal('0')
        sgst = orders.aggregate(total=Sum('sgst'))['total'] or Decimal('0')
        igst = orders.aggregate(total=Sum('igst'))['total'] or Decimal('0')
        cess = orders.aggregate(total=Sum('cess'))['total'] or Decimal('0')
        
        # Exempt Sales (orders with 0 tax)
        exempt_sales = orders.filter(tax_amount=0).aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
        # Non-Taxable Sales (untaxed portion of partially taxed orders)
        non_taxable_sales = orders.filter(tax_amount__gt=0).aggregate(total=Sum(F('subtotal') - F('taxable_amount')))['total'] or Decimal('0')

        # Global KPIs (regardless of date filter)
        now = timezone.now()
        base_orders = Order.objects.filter(status=OrderStatus.SETTLED)
        if branch_id:
            base_orders = base_orders.filter(location_id=branch_id)
            
        daily_gst = base_orders.filter(opened_at__date=now.date()).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        monthly_gst = base_orders.filter(opened_at__year=now.year, opened_at__month=now.month).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        yearly_gst = base_orders.filter(opened_at__year=now.year).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')

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
            'exempt_sales': exempt_sales,
            'non_taxable_sales': non_taxable_sales,
            'total_tax': total_tax,
            'cgst': cgst,
            'sgst': sgst,
            'igst': igst,
            
            'daily_gst': daily_gst,
            'monthly_gst': monthly_gst,
            'yearly_gst': yearly_gst,
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
            branch = Branch.objects.get(id=getattr(order, 'location_id', None))
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
            'tenant_id': getattr(self.request, 'tenant_id', None),
        })
        return context


class InvoiceDownloadPDFView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """Download a PDF copy of an invoice using WeasyPrint."""
    permission_required = "invoices.view"

    def get(self, request, order_id, **kwargs):
        from contexts.reporting.services.pdf_generator import generate_invoice_pdf
        try:
            filename, pdf_bytes = generate_invoice_pdf(str(order_id))
        except Exception as e:
            from django.http import HttpResponseServerError
            return HttpResponseServerError(f"Could not generate PDF: {e}")

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class TaxSummaryView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/tax_summary.html"
    permission_required = "reports.financial.view"

    def get(self, request, *args, **kwargs):
        preset = request.GET.get('preset', 'this_month')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        start_dt, end_dt, start_date, end_date = get_date_range(preset, start_date_str, end_date_str)
        
        branch_id = request.GET.get('branch')
        cashier_id = request.GET.get('cashier')
        
        # Base query (don't limit to SETTLED so we can calculate outstanding tax)
        orders = Order.objects.filter(
            opened_at__gte=start_dt,
            opened_at__lte=end_dt
        ).exclude(status=OrderStatus.VOID)
        
        if branch_id:
            orders = orders.filter(location_id=branch_id)
        if cashier_id:
            orders = orders.filter(created_by=cashier_id)

        record_audit("reports.tax_summary.view", entity_type="report", changes={"preset": preset})

        # Base Aggregations
        taxable_sales = orders.filter(tax_amount__gt=0).aggregate(total=Sum('taxable_amount'))['total'] or Decimal('0')
        total_tax = orders.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        cgst = orders.aggregate(total=Sum('cgst'))['total'] or Decimal('0')
        sgst = orders.aggregate(total=Sum('sgst'))['total'] or Decimal('0')
        igst = orders.aggregate(total=Sum('igst'))['total'] or Decimal('0')
        
        # Exempt Sales (orders with 0 tax)
        exempt_sales = orders.filter(tax_amount=0).aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
        
        # Outstanding Tax vs Tax Collected
        # Tax Collected: from orders fully or partially paid. To be precise, we can approximate that 
        # tax collected is (paid_amount / total) * tax_amount, but typically if due_amount > 0, it's outstanding.
        # Let's simplify: if due_amount > 0, the proportion of unpaid tax is outstanding.
        # Or even simpler: Sum tax of unpaid/partially paid vs settled.
        tax_collected = orders.filter(due_amount=0).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        outstanding_tax = orders.filter(due_amount__gt=0).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        # Charts
        # 1. Tax Collection by Payment Status
        status_labels = ["Collected", "Outstanding"]
        status_data = [float(tax_collected), float(outstanding_tax)]
        
        # 2. Daily GST Timeline
        daily_tax = list(orders.annotate(day=TruncDate('opened_at')).values('day').annotate(total=Sum('tax_amount')).order_by('day'))
        day_labels = [d['day'].strftime('%d %b') for d in daily_tax if d['day']]
        day_data = [float(d['total']) for d in daily_tax]

        # Cashiers for filter dropdown
        from contexts.identity.models import User
        cashier_ids = orders.values_list('created_by', flat=True).distinct()
        cashiers = User.objects.filter(id__in=cashier_ids)

        export_format = request.GET.get('export')
        if export_format:
            record_audit("reports.tax_summary.export", entity_type="report", changes={"format": export_format, "preset": preset})
            header = ['Metric', 'Value (INR)']
            rows = [
                ['Total GST', f"{total_tax:.2f}"],
                ['CGST', f"{cgst:.2f}"],
                ['SGST', f"{sgst:.2f}"],
                ['IGST', f"{igst:.2f}"],
                ['Taxable Sales', f"{taxable_sales:.2f}"],
                ['Exempt Sales', f"{exempt_sales:.2f}"],
                ['Tax Collected', f"{tax_collected:.2f}"],
                ['Outstanding Tax', f"{outstanding_tax:.2f}"],
            ]
            return generate_export_response(header, rows, export_format, 'tax_summary_report')

        context = self.get_context_data(**kwargs)
        context.update({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'preset': preset,
            'branches': Branch.objects.filter(is_active=True),
            'selected_branch': branch_id or '',
            'cashiers': cashiers,
            'selected_cashier': cashier_id or '',
            
            'taxable_sales': taxable_sales,
            'exempt_sales': exempt_sales,
            'total_tax': total_tax,
            'cgst': cgst,
            'sgst': sgst,
            'igst': igst,
            'tax_collected': tax_collected,
            'outstanding_tax': outstanding_tax,
            
            'status_labels': status_labels,
            'status_data': status_data,
            'day_labels': day_labels,
            'day_data': day_data,
        })
        return self.render_to_response(context)


class EmailShareModalView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/email_modal.html"
    permission_required = "invoices.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order.objects.select_related('invoice'), id=order_id)
        
        branch_name = "our store"
        try:
            branch = Branch.objects.get(id=getattr(order, 'location_id', None))
            branch_name = branch.name
        except Branch.DoesNotExist:
            pass

        customer_name = order.customer_name or "Valued Customer"
        invoice_num = order.invoice.number if hasattr(order, 'invoice') else order.order_number
        
        default_subject = f"Your Invoice #{invoice_num} from {branch_name}"
        default_message = (
            f"Dear {customer_name},\n\n"
            f"Thank you for visiting {branch_name}!\n"
            f"Please find your invoice #{invoice_num} attached as a PDF.\n\n"
            f"We look forward to serving you again."
        )
        
        context.update({
            'order': order,
            'customer_email': order.customer_email or "",
            'default_subject': default_subject,
            'default_message': default_message,
        })
        return context


class EmailInvoiceView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "invoices.view"

    def post(self, request, *args, **kwargs):
        import json
        from django.http import JsonResponse
        from contexts.notifications.services import create_notification
        from contexts.notifications.models import ChannelType
        
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        try:
            body = json.loads(request.body.decode('utf-8'))
            recipient_email = body.get('email')
            subject = body.get('subject')
            message_text = body.get('message_text')
        except Exception:
            recipient_email = request.POST.get('email') or order.customer_email
            subject = request.POST.get('subject', 'Invoice')
            message_text = request.POST.get('message_text', 'Please find your invoice attached.')
            
        if not recipient_email:
            return JsonResponse({'status': 'error', 'message': 'No recipient email specified.'}, status=400)
            
        # Create an async notification with the PDF attachment instruction
        create_notification(
            tenant_id=request.tenant_id,
            channel=ChannelType.EMAIL,
            recipient=recipient_email,
            context_data={
                "subject": subject,
                "body": message_text,
                "_attachment_instruction": {
                    "type": "invoice_pdf",
                    "order_id": str(order.id)
                }
            }
        )

        record_audit("invoice.emailed", entity_type="invoice", entity_id=order.id, changes={"recipient": recipient_email})
        return JsonResponse({
            'status': 'success',
            'message': f'Invoice successfully queued for email delivery to {recipient_email}.'
        })


class InvoiceListView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/invoice_list.html"
    permission_required = "invoices.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Invoice.objects.select_related('order').prefetch_related('order__payments').order_by('-issued_at')
        
        # 1. Search Query
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(number__icontains=query) |
                Q(order__order_number__icontains=query) |
                Q(order__customer_phone__icontains=query) |
                Q(order__customer_name__icontains=query)
            )

        # 2. Date Range
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                start_aware = timezone.make_aware(datetime.combine(start_dt, time.min))
                end_aware = timezone.make_aware(datetime.combine(end_dt, time.max))
                qs = qs.filter(issued_at__gte=start_aware, issued_at__lte=end_aware)
            except ValueError:
                pass
            
        # 3. Branch Filter
        branch_id = self.request.GET.get('branch_id')
        if branch_id:
            qs = qs.filter(location_id=branch_id)
            
        # 4. Status Filter
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        # 5. Sort Order
        sort = self.request.GET.get('sort', '-issued_at')
        if sort in ['issued_at', '-issued_at', 'total', '-total']:
            qs = qs.order_by(sort)

        branches = Branch.objects.filter(is_active=True)
        user_map = {str(u.id): u.full_name or u.email for u in User.objects.all()}
        branch_map = {str(b.id): b.name for b in branches}
        
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        for inv in page_obj:
            inv.branch_name = branch_map.get(str(inv.location_id), "Unknown")
            inv.cashier_name = user_map.get(str(inv.order.created_by), "System")
            payments = inv.order.payments.all()
            if payments:
                methods = set(p.method for p in payments)
                inv.payment_method_display = "SPLIT" if len(methods) > 1 else methods.pop()
            else:
                inv.payment_method_display = "UNPAID"

        context.update({
            'page_obj': page_obj,
            'query': query or '',
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
            'selected_branch': branch_id or '',
            'selected_status': status or '',
            'sort': sort,
            'branches': branches,
            'statuses': InvoiceStatus.choices,
            'tenant_id': getattr(self.request, 'tenant_id', None),
        })
        return context


class PaymentHistoryView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/payment_history.html"
    permission_required = "reports.financial.view"

    def get(self, request, *args, **kwargs):
        export_format = request.GET.get('export')
        if export_format:
            return self.export_data(export_format)
        return super().get(request, *args, **kwargs)

    def export_data(self, export_format):
        qs = self.get_queryset()
        branches = Branch.objects.filter(is_active=True)
        user_map = {str(u.id): u.full_name or u.email for u in User.objects.all()}
        branch_map = {str(b.id): b.name for b in branches}
        
        record_audit("reports.financial.export", entity_type="report", changes={"format": export_format})
        header = ['Transaction ID', 'Date & Time', 'Invoice #', 'Order #', 'Customer', 'Amount', 'Payment Method', 'Status', 'Cashier', 'Branch']
        rows = []
        for p in qs:
            branch_name = branch_map.get(str(p.getattr(order, 'location_id', None)), "Unknown")
            cashier_name = user_map.get(str(p.created_by), "System")
            invoice_num = p.order.invoice.number if hasattr(p.order, 'invoice') else "N/A"
            rows.append([
                p.reference or str(p.id)[:8],
                p.captured_at.strftime('%Y-%m-%d %H:%M'),
                invoice_num,
                p.order.order_number,
                p.order.customer_name or 'Guest',
                p.amount,
                p.method,
                p.status,
                cashier_name,
                branch_name
            ])
        return generate_export_response(header, rows, export_format, 'payment_history')

    def get_queryset(self):
        qs = Payment.objects.select_related('order', 'order__invoice').order_by('-captured_at')
        
        # Search Query
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(reference__icontains=query) |
                Q(order__order_number__icontains=query) |
                Q(order__customer_name__icontains=query) |
                Q(order__customer_phone__icontains=query) |
                Q(order__invoice__number__icontains=query)
            )

        # Date Range
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                start_aware = timezone.make_aware(datetime.combine(start_dt, time.min))
                end_aware = timezone.make_aware(datetime.combine(end_dt, time.max))
                qs = qs.filter(captured_at__gte=start_aware, captured_at__lte=end_aware)
            except ValueError:
                pass
                
        # Method Filter
        method = self.request.GET.get('method')
        if method:
            qs = qs.filter(method=method)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        branches = Branch.objects.filter(is_active=True)
        user_map = {str(u.id): u.full_name or u.email for u in User.objects.all()}
        branch_map = {str(b.id): b.name for b in branches}

        for p in page_obj:
            p.branch_name = branch_map.get(str(p.getattr(order, 'location_id', None)), "Unknown")
            p.cashier_name = user_map.get(str(p.created_by), "System")
        
        # Get total collected today
        today = timezone.localdate()
        today_payments = Payment.objects.filter(
            captured_at__date=today,
            status=PaymentStatus.CAPTURED
        )
        total_today = today_payments.aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
        
        context.update({
            'page_obj': page_obj,
            'query': self.request.GET.get('q', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'selected_method': self.request.GET.get('method', ''),
            'total_today': total_today,
            'methods': PaymentMethod.choices,
            'tenant_id': getattr(self.request, 'tenant_id', None),
        })
        return context


class WhatsAppShareModalView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/whatsapp_modal.html"
    permission_required = "invoices.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order.objects.select_related('invoice'), id=order_id)
        
        branch_name = "our store"
        try:
            branch = Branch.objects.get(id=getattr(order, 'location_id', None))
            branch_name = branch.name
        except Branch.DoesNotExist:
            pass

        customer_name = order.customer_name or "Valued Customer"
        invoice_num = order.invoice.number if hasattr(order, 'invoice') else order.order_number
        total = _fmt_inr(order.total)
        
        # Build secure link (using the absolute URL for the invoice detail)
        # Assuming the domain will be determined by the host
        domain = self.request.build_absolute_uri('/')[:-1]
        link = f"{domain}/reporting/invoice/{order.id}/"
        
        default_message = (
            f"Dear {customer_name},\n\n"
            f"Thank you for visiting {branch_name}!\n"
            f"Your invoice #{invoice_num} for ₹{total} is ready.\n\n"
            f"View your secure invoice here: {link}\n\n"
            f"We look forward to serving you again."
        )
        
        context.update({
            'order': order,
            'customer_phone': order.customer_phone or "",
            'default_message': default_message,
        })
        return context


class WhatsAppSendActionView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "invoices.view"

    def post(self, request, *args, **kwargs):
        import json
        from django.http import JsonResponse
        from contexts.reporting.services.whatsapp import WhatsAppSharingService
        
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        try:
            body = json.loads(request.body.decode('utf-8'))
            phone_number = body.get('phone_number')
            message_text = body.get('message_text')
        except Exception:
            phone_number = request.POST.get('phone_number')
            message_text = request.POST.get('message_text')
            
        if not phone_number or not message_text:
            return JsonResponse({'status': 'error', 'message': 'Phone number and message are required.'}, status=400)
            
        wa_link = WhatsAppSharingService.log_and_send_whatsapp(
            tenant_id=request.tenant_id,
            phone_number=phone_number,
            message_text=message_text,
            context_data={'order_id': str(order.id)}
        )
        
        # Record local audit
        record_audit("invoice.whatsapp_shared", entity_type="invoice", entity_id=order.id, changes={"phone": phone_number})
        
        return JsonResponse({
            'status': 'success',
            'redirect_url': wa_link,
            'message': 'WhatsApp link generated and logged successfully.'
        })


class InvoiceHistoryModalView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/invoice_history_modal.html"
    permission_required = "invoices.view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = kwargs.get('order_id')
        order = get_object_or_404(Order.objects.select_related('invoice'), id=order_id)
        
        from contexts.audit.models import AuditLog
        from contexts.identity.models import User
        
        # Get all audit logs for this order or invoice
        entity_ids = [order.id]
        if hasattr(order, 'invoice') and order.invoice:
            entity_ids.append(order.invoice.id)
            
        logs = AuditLog.objects.filter(entity_id__in=entity_ids).order_by('-occurred_at')
        
        user_ids = [log.actor_id for log in logs if log.actor_id]
        users = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}
        
        annotated_logs = []
        for log in logs:
            log.actor_name = users.get(str(log.actor_id)).full_name if str(log.actor_id) in users else "System"
            annotated_logs.append(log)
            
        context.update({
            'order': order,
            'logs': annotated_logs,
        })
        return context


class BillingAuditLogView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "reporting/billing_audit_log.html"
    permission_required = "reports.financial.view"

    def get_queryset(self):
        from contexts.audit.models import AuditLog
        qs = AuditLog.objects.filter(entity_type__in=["order", "invoice", "payment"]).order_by('-occurred_at')
        
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
            
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                start_aware = timezone.make_aware(datetime.combine(start_dt, time.min))
                end_aware = timezone.make_aware(datetime.combine(end_dt, time.max))
                qs = qs.filter(occurred_at__gte=start_aware, occurred_at__lte=end_aware)
            except ValueError:
                pass
                
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        paginator = Paginator(qs, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        from contexts.identity.models import User
        user_ids = set([log.actor_id for log in page_obj if log.actor_id])
        users = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}
        
        for log in page_obj:
            log.actor_name = users.get(str(log.actor_id)).full_name if str(log.actor_id) in users else "System"
            
        context.update({
            'page_obj': page_obj,
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'selected_action': self.request.GET.get('action', ''),
            'actions': [
                "order.created", "order.split", "order.merged", "order.item_voided", "order.voided",
                "invoice.issued", "invoice.voided", "invoice.whatsapp_shared", 
                "payment.captured", "payment.refunded"
            ]
        })
        return context

from django.views.generic import TemplateView, View, ListView

from contexts.reporting.services.gst_filing_service import GSTFilingService
from contexts.ordering.models import Refund
from contexts.tenants.models import TenantConfiguration

class GSTFilingView(TenantPermissionRequiredMixin, TemplateView):
    """
    Enterprise dashboard for generating GST filing extracts (GSTR-1, GSTR-3B).
    """
    permission_required = "reports.financial.view"
    template_name = "reporting/gst_filing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date_str = self.request.GET.get("start_date", timezone.now().date().isoformat())
        end_date_str = self.request.GET.get("end_date", timezone.now().date().isoformat())
        
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        
        context["start_date"] = start_date_str
        context["end_date"] = end_date_str
        
        context["hsn_summary"] = GSTFilingService.get_hsn_summary(start_date, end_date)
        context["b2b_b2c"] = GSTFilingService.get_b2b_b2c_summary(start_date, end_date)
        context["tenant_id"] = getattr(self.request, 'tenant_id', None)
        
        return context

class RefundBillsView(TenantPermissionRequiredMixin, ListView):
    """
    Dashboard for monitoring and processing refunds.
    """
    permission_required = "reports.financial.view"
    template_name = "reporting/refund_bills.html"
    context_object_name = "refunds"
    paginate_by = 25
    
    def get_queryset(self):
        qs = Refund.objects.all().select_related("order")
        
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant_id"] = getattr(self.request, 'tenant_id', None)
        context["target_order_id"] = self.request.GET.get("order", "")
        return context


class RefundLookupView(TenantPermissionRequiredMixin, View):
    """
    API endpoint to look up order/invoice details for refund initiation.
    """
    permission_required = "reports.financial.view"

    def has_permission(self):
        if getattr(self.request.user, "is_superuser", False):
            return True
        tenant_id = getattr(self.request, "tenant_id", None)
        location_id = getattr(self.request, "branch_id", None)
        for perm in ["reports.financial.view", "payments.refund", "orders.void", "invoices.void", "billing.manage"]:
            if has_permission(self.request.user, perm, tenant_id):
                return True
        return False

    def get(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from contexts.ordering.models import Order, RefundStatus
        from contexts.ordering.domain.enums import PaymentKind

        query = request.GET.get("query", "").strip()
        order_id = request.GET.get("order_id", "").strip()

        order = None
        def _lookup():
            if order_id:
                try:
                    return Order.objects.filter(id=order_id).first()
                except Exception:
                    return None
            elif query:
                return (
                    Order.objects.filter(order_number__iexact=query).first()
                    or Order.objects.filter(invoice__number__iexact=query).first()
                    or Order.objects.filter(order_number__icontains=query).first()
                )
            return None

        order = _lookup()
        if not order and get_current_tenant() is None:
            with bypass_tenant():
                order = _lookup()

        if not order:
            return JsonResponse({"success": False, "error": "Order or invoice not found."}, status=404)

        already_refunded = sum(r.amount for r in order.refunds.filter(status=RefundStatus.COMPLETED))
        refundable_balance = max(Decimal("0.00"), order.total - already_refunded)

        orig_pm = order.payments.filter(kind=PaymentKind.PAYMENT).first()
        payment_method = orig_pm.method if orig_pm else "CASH"

        inv_number = order.invoice.number if hasattr(order, "invoice") and order.invoice else None

        items = [
            {
                "name": item.name_snapshot,
                "qty": float(item.qty),
                "price": float(item.unit_price)
            }
            for item in order.items.all()
        ]

        return JsonResponse({
            "success": True,
            "order": {
                "id": str(order.id),
                "order_number": order.order_number,
                "invoice_number": inv_number or "",
                "customer_name": order.customer_name or "Walk-in Customer",
                "date": order.created_at.strftime("%b %d, %Y %I:%M %p"),
                "status": order.status,
                "total": float(order.total),
                "already_refunded": float(already_refunded),
                "refundable_balance": float(refundable_balance),
                "payment_method": payment_method,
                "items": items
            }
        })


class InitiateRefundView(TenantPermissionRequiredMixin, View):
    """
    POST API endpoint to initiate and execute an order/invoice refund.
    """
    permission_required = "reports.financial.view"

    def has_permission(self):
        if getattr(self.request.user, "is_superuser", False):
            return True
        tenant_id = getattr(self.request, "tenant_id", None)
        location_id = getattr(self.request, "branch_id", None)
        for perm in ["reports.financial.view", "payments.refund", "orders.void", "invoices.void", "billing.manage"]:
            if has_permission(self.request.user, perm, tenant_id):
                return True
        return False

    def post(self, request, *args, **kwargs):
        import json
        from django.http import JsonResponse
        from contexts.ordering.services.refund_service import initiate_refund

        data = {}
        if request.content_type and "application/json" in request.content_type:
            try:
                data = json.loads(request.body)
            except Exception:
                return JsonResponse({"success": False, "error": "Invalid JSON payload."}, status=400)
        else:
            data = request.POST

        order_id_str = data.get("order_id")
        amount_str = data.get("amount")
        reason = data.get("reason", "").strip()
        refund_type = data.get("refund_type", "FULL")
        payment_method = data.get("payment_method") or None
        restock_str = str(data.get("restock_inventory", "true")).lower()
        restock_inventory = restock_str in ("1", "true", "yes", "on")

        if not order_id_str or not amount_str or not reason:
            return JsonResponse({
                "success": False,
                "error": "Order ID, Refund Amount, and Refund Reason are required."
            }, status=400)

        try:
            import uuid
            order_id = uuid.UUID(order_id_str)
            amount = Decimal(str(amount_str))
        except Exception:
            return JsonResponse({"success": False, "error": "Invalid Order ID or Amount format."}, status=400)

        try:
            refund = initiate_refund(
                order_id=order_id,
                amount=amount,
                reason=reason,
                refund_type=refund_type,
                payment_method=payment_method,
                restock_inventory=restock_inventory,
                requested_by=request.user.id
            )
            return JsonResponse({
                "success": True,
                "refund_id": str(refund.id),
                "message": f"Refund of ₹{refund.amount:.2f} processed successfully."
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


class WhatsAppHistoryView(TenantPermissionRequiredMixin, TemplateView):
    """
    Global dashboard for WhatsApp message history.
    """
    permission_required = "reports.financial.view"
    template_name = "reporting/whatsapp_history.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # We fetch audit logs corresponding to whatsapp shares
        from contexts.audit.models import AuditLog
        logs = AuditLog.objects.filter(
            action="invoice.whatsapp_shared"
        ).order_by("-occurred_at")[:50]
        
        context["history"] = logs
        context["tenant_id"] = getattr(self.request, 'tenant_id', None)
        return context

class BillingSettingsView(TenantPermissionRequiredMixin, TemplateView):
    """
    Dashboard for configuring billing-specific tenant settings.
    """
    permission_required = "reports.financial.view"
    template_name = "reporting/billing_settings.html"

    def _get_or_create_config(self):
        config = TenantConfiguration.objects.first()
        if not config:
            tenant_id = getattr(self.request, "tenant_id", None)
            config = TenantConfiguration.objects.create(tenant_id=tenant_id)
        return config
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = self._get_or_create_config()
        context["tenant_id"] = getattr(self.request, 'tenant_id', None)
        return context

    def post(self, request, *args, **kwargs):
        config = self._get_or_create_config()
        
        config.invoice_prefix = request.POST.get("invoice_prefix", "INV")
        config.invoice_footer = request.POST.get("invoice_footer", "")
        config.gst_number = request.POST.get("gst_number", "")
        config.save()
        
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id:
            return redirect("billing:settings_tenant", tenant_id=tenant_id)
        return redirect("billing:settings")
