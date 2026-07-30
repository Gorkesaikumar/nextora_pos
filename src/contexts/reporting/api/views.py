"""Reporting and Dashboard API views."""
from decimal import Decimal
from datetime import datetime, time, timedelta

from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate, TruncMonth, ExtractHour, TruncWeek
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from shared.api.views import BaseAPIView
from shared.tenancy.context import get_current_tenant
from contexts.ordering.models import Order, OrderItem, KOT, Payment
from contexts.ordering.domain.enums import OrderStatus, KOTStatus, PaymentStatus, PaymentKind
from contexts.catalog.models import Product
from contexts.inventory.models import InventoryItem
from contexts.reporting.services.gst_filing_service import GSTFilingService
from contexts.reporting.views import get_date_range, generate_export_response
from .serializers import (
    DashboardSummarySerializer,
    SalesMetricItemSerializer,
    TopItemSerializer,
    TopCategorySerializer,
    PaymentMethodSummarySerializer,
    GSTSummarySerializer,
    SalesChartPointSerializer,
    ProfitReportItemSerializer,
    KDSMetricsSerializer
)


class BaseReportingView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_date_bounds(self, request):
        preset = request.query_params.get("preset", "today")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        start_dt, end_dt, start_date, end_date = get_date_range(preset, start_date_str, end_date_str)
        return start_dt, end_dt

    def _get_settled_orders(self, request, start_dt, end_dt):
        tenant_id = get_current_tenant()
        return Order.objects.filter(
            tenant_id=tenant_id,
            status=OrderStatus.SETTLED,
            opened_at__gte=start_dt,
            opened_at__lte=end_dt
        )


class DashboardSummaryView(BaseReportingView):
    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request, *args, **kwargs) -> Response:
        tenant_id = get_current_tenant()
        today = timezone.localdate()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))

        orders = Order.objects.filter(tenant_id=tenant_id, opened_at__gte=today_start, opened_at__lte=today_end)
        active_orders = orders.exclude(status=OrderStatus.VOID)

        revenue_today = active_orders.aggregate(sum=Sum('total'))['sum'] or Decimal("0.00")
        orders_today = active_orders.count()
        avg_ticket = (revenue_today / Decimal(orders_today)) if orders_today > 0 else Decimal("0.00")
        active_tables = orders.filter(status=OrderStatus.OPEN, type="dine_in").count()
        open_kots = KOT.objects.filter(order__tenant_id=tenant_id, status__in=[KOTStatus.NEW, KOTStatus.PREPARING]).count()
        
        refunds_today = Payment.objects.filter(
            order__in=orders, status=PaymentStatus.CAPTURED, kind=PaymentKind.REFUND
        ).aggregate(sum=Sum('amount'))['sum'] or Decimal("0.00")

        pending_payments = orders.exclude(status__in=[OrderStatus.SETTLED, OrderStatus.VOID]).aggregate(sum=Sum('total'))['sum'] or Decimal("0.00")

        data = {
            "sales_today": revenue_today,
            "orders_today": orders_today,
            "active_tables": active_tables,
            "average_ticket": avg_ticket,
            "open_kots": open_kots,
            "refunds_today": refunds_today,
            "pending_payments": pending_payments,
        }
        return Response(data, status=status.HTTP_200_OK)


class SalesMetricsView(BaseReportingView):
    @extend_schema(responses=SalesMetricItemSerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        period = request.query_params.get("period", "daily") # daily, weekly, monthly, yearly
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)

        if period == "weekly":
            trunc_func = TruncWeek('opened_at')
        elif period == "monthly":
            trunc_func = TruncMonth('opened_at')
        elif period == "yearly":
            # Using TruncMonth then grouping manually, or just total for year if simple
            # We'll stick to month for this implementation for robustness across DBs
            trunc_func = TruncMonth('opened_at')
        else: # daily
            trunc_func = TruncDate('opened_at')

        aggregated = settled.annotate(period_group=trunc_func).values('period_group').annotate(
            orders_count=Count('id'),
            gross_sales=Sum('subtotal'),
            discounts=Sum('discount_amount'),
            taxes=Sum('tax_amount'),
            net_sales=Sum('total')
        ).order_by('-period_group')

        results = []
        for d in aggregated:
            period_str = d['period_group'].isoformat() if d['period_group'] else "Unknown"
            results.append({
                "period": period_str,
                "orders_count": d['orders_count'],
                "gross_sales": d['gross_sales'],
                "discounts": d['discounts'],
                "taxes": d['taxes'],
                "net_sales": d['net_sales']
            })
        return Response(results, status=status.HTTP_200_OK)


class TopSellingItemsView(BaseReportingView):
    @extend_schema(responses=TopItemSerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)

        items = OrderItem.objects.filter(order__in=settled)
        item_stats = list(items.values('product_id', 'name_snapshot').annotate(
            qty_sold=Sum('qty'),
            revenue=Sum('line_total')
        ).order_by('-qty_sold')[:20])

        product_ids = [i['product_id'] for i in item_stats]
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        prod_cat_map = {p.id: p.category.name if p.category else "Other" for p in products}

        # Simplified Profit logic: if we don't have cost in inventory, assume 0 for placeholder
        inventory_items = InventoryItem.objects.filter(product_id__in=product_ids)
        prod_cost_map = {i.product_id: i.average_cost for i in inventory_items}

        results = []
        for i in item_stats:
            p_id = i['product_id']
            qty = i['qty_sold'] or Decimal("0")
            rev = i['revenue'] or Decimal("0")
            cost = prod_cost_map.get(p_id, Decimal("0")) * qty
            profit = rev - cost

            results.append({
                "product_id": str(p_id),
                "name": i['name_snapshot'],
                "category": prod_cat_map.get(p_id, "Other"),
                "qty_sold": qty,
                "revenue": rev,
                "profit": profit
            })

        return Response(results, status=status.HTTP_200_OK)


class TopCategoriesView(BaseReportingView):
    @extend_schema(responses=TopCategorySerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)
        items = OrderItem.objects.filter(order__in=settled)
        
        product_ids = list(items.values_list('product_id', flat=True).distinct())
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        prod_cat_map = {p.id: p.category.name if p.category else 'Other' for p in products}
        
        cat_stats = {}
        total_revenue = Decimal("0")
        
        for item in items:
            cat_name = prod_cat_map.get(item.product_id, 'Other')
            if cat_name not in cat_stats:
                cat_stats[cat_name] = {"revenue": Decimal("0"), "items_sold": Decimal("0")}
            cat_stats[cat_name]["revenue"] += item.line_total
            cat_stats[cat_name]["items_sold"] += item.qty
            total_revenue += item.line_total
            
        results = []
        for cat, stats in cat_stats.items():
            pct = float((stats["revenue"] / total_revenue) * 100) if total_revenue > 0 else 0.0
            results.append({
                "category": cat,
                "revenue": stats["revenue"],
                "items_sold": stats["items_sold"],
                "percentage": round(pct, 2)
            })
            
        results.sort(key=lambda x: x["revenue"], reverse=True)
        return Response(results, status=status.HTTP_200_OK)


class PaymentSummaryView(BaseReportingView):
    @extend_schema(responses=PaymentMethodSummarySerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)
        
        payment_data = Payment.objects.filter(
            order__in=settled, kind=PaymentKind.PAYMENT, status=PaymentStatus.CAPTURED
        ).values('method').annotate(transactions=Count('id'), total_amount=Sum('amount')).order_by('-total_amount')
        
        results = [
            {
                "method": d['method'],
                "transactions": d['transactions'],
                "total_amount": d['total_amount'] or Decimal("0")
            }
            for d in payment_data
        ]
        return Response(results, status=status.HTTP_200_OK)


class GSTReportsView(BaseReportingView):
    @extend_schema(responses=GSTSummarySerializer)
    def get(self, request, *args, **kwargs) -> Response:
        _, _, start_date, end_date = get_date_range(
            request.query_params.get("preset", "this_month"),
            request.query_params.get("start_date"),
            request.query_params.get("end_date")
        )
        
        hsn = GSTFilingService.get_hsn_summary(start_date, end_date)
        b2b_b2c = GSTFilingService.get_b2b_b2c_summary(start_date, end_date)
        
        # Make safe for serialization
        for entry in hsn:
            if 'tax_percentage' in entry and type(entry['tax_percentage']) == Decimal:
                entry['tax_percentage'] = float(entry['tax_percentage'])
                
        return Response({
            "hsn_summary": hsn,
            "b2b_b2c_summary": b2b_b2c
        }, status=status.HTTP_200_OK)


class SalesChartsView(BaseReportingView):
    @extend_schema(responses=SalesChartPointSerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)
        interval = request.query_params.get("interval", "daily") # hourly, daily
        
        if interval == "hourly":
            trend = list(settled.annotate(hour=ExtractHour('opened_at')).values('hour').annotate(revenue=Sum('total')).order_by('hour'))
            results = [{"label": f"{d['hour']}:00", "value": float(d['revenue'])} for d in trend]
        else: # daily
            trend = list(settled.annotate(date=TruncDate('opened_at')).values('date').annotate(revenue=Sum('total')).order_by('date'))
            results = [{"label": d['date'].strftime('%b %d') if d['date'] else "", "value": float(d['revenue'])} for d in trend]

        return Response(results, status=status.HTTP_200_OK)


class ProfitReportsView(BaseReportingView):
    @extend_schema(responses=ProfitReportItemSerializer(many=True))
    def get(self, request, *args, **kwargs) -> Response:
        start_dt, end_dt = self._get_date_bounds(request)
        settled = self._get_settled_orders(request, start_dt, end_dt)
        
        items = OrderItem.objects.filter(order__in=settled)
        item_stats = list(items.values('product_id', 'name_snapshot').annotate(
            qty_sold=Sum('qty'),
            revenue=Sum('line_total')
        ).order_by('-revenue'))
        
        product_ids = [i['product_id'] for i in item_stats]
        inventory_items = InventoryItem.objects.filter(product_id__in=product_ids)
        prod_cost_map = {i.product_id: i.average_cost for i in inventory_items}
        
        results = []
        for i in item_stats:
            p_id = i['product_id']
            qty = i['qty_sold'] or Decimal("0")
            rev = i['revenue'] or Decimal("0")
            unit_cost = prod_cost_map.get(p_id, Decimal("0"))
            cost = unit_cost * qty
            profit = rev - cost
            margin = float((profit / rev) * 100) if rev > 0 else 0.0
            
            results.append({
                "name": i['name_snapshot'],
                "revenue": rev,
                "cost": cost,
                "profit": profit,
                "margin_percentage": round(margin, 2)
            })
            
        return Response(results, status=status.HTTP_200_OK)


from contexts.reporting.services.export_service import ExportService
from rest_framework.parsers import JSONParser

class ExportAPIView(BaseReportingView):
    parser_classes = [JSONParser]
    
    def post(self, request, *args, **kwargs) -> Response:
        report_type = request.data.get("report_type", "sales")
        export_format = request.data.get("format", "csv")
        start_date = request.data.get("start_date", "")
        end_date = request.data.get("end_date", "")
        
        tenant_id = get_current_tenant()
        user = request.user
        
        try:
            return ExportService.generate(
                tenant_id=tenant_id,
                report_type=report_type,
                export_format=export_format,
                start_date=start_date,
                end_date=end_date,
                user=user
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to generate report: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KDSMetricsView(BaseReportingView):
    @extend_schema(responses=KDSMetricsSerializer)
    def get(self, request, *args, **kwargs) -> Response:
        tenant_id = get_current_tenant()
        now = timezone.now()
        today_start = timezone.make_aware(datetime.combine(now.date(), time.min))
        today_end = timezone.make_aware(datetime.combine(now.date(), time.max))

        kots_today = KOT.objects.filter(tenant_id=tenant_id, created_at_kot__gte=today_start, created_at_kot__lte=today_end)
        
        # Real-time state
        waiting = kots_today.filter(status=KOTStatus.NEW).count()
        preparing = kots_today.filter(status=KOTStatus.PREPARING).count()
        ready = kots_today.filter(status=KOTStatus.READY).count()
        
        # Delayed (Elapsed > 15m and still NEW/PREPARING)
        delayed_threshold = now - timedelta(minutes=15)
        delayed = kots_today.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING],
            created_at_kot__lt=delayed_threshold
        ).count()
        
        total_today = kots_today.count()
        completed_today = kots_today.filter(status__in=[KOTStatus.READY, KOTStatus.SERVED]).count()
        completion_rate = int((completed_today / total_today * 100)) if total_today > 0 else 0
        
        # Kitchen Efficiency (Percentage of completed that were NOT delayed)
        # For simplicity, if we don't track completion time precisely, we estimate:
        efficiency = 100 - int((delayed / total_today * 100)) if total_today > 0 else 100
        
        # Station Utilization
        from contexts.restaurant.models.kitchen import KitchenStation
        stations = KitchenStation.objects.filter(is_active=True)
        station_utilization = []
        for station in stations:
            active_kots = kots_today.filter(
                kitchen_station_id=station.id, 
                status__in=[KOTStatus.NEW, KOTStatus.PREPARING]
            ).count()
            station_utilization.append({
                "station_id": station.id,
                "station_name": station.name,
                "active_kots": active_kots
            })

        # Sort stations by utilization
        station_utilization.sort(key=lambda x: x["active_kots"], reverse=True)

        return Response({
            "waiting": waiting,
            "preparing": preparing,
            "ready": ready,
            "delayed": delayed,
            "avg_prep_time": "12m 30s", # Hardcoded or placeholder until explicit completion tracking is added
            "completion_rate": completion_rate,
            "orders_today": total_today,
            "kitchen_efficiency": max(0, min(100, efficiency)),
            "station_utilization": station_utilization
        }, status=status.HTTP_200_OK)
