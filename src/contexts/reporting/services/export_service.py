from decimal import Decimal
import datetime
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import HttpResponse

from contexts.ordering.models import Order, OrderItem, Payment
from contexts.ordering.domain.enums import OrderStatus, PaymentStatus, PaymentKind
from contexts.catalog.models import Product
from contexts.inventory.models import InventoryItem
from contexts.reporting.services.gst_filing_service import GSTFilingService

from .csv_export import CSVExportService
from .excel_export import ExcelExportService
from .pdf_export import PDFExportService


class ExportService:
    @staticmethod
    def generate(tenant_id, report_type: str, export_format: str, start_date: str, end_date: str, user):
        # 1. Parse Dates
        try:
            start_dt = timezone.make_aware(datetime.datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S.%f')) if 'T' in start_date else timezone.make_aware(datetime.datetime.strptime(start_date, '%Y-%m-%d'))
            end_dt = timezone.make_aware(datetime.datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S.%f')) if 'T' in end_date else timezone.make_aware(datetime.datetime.strptime(end_date, '%Y-%m-%d'))
            # Move end to end of day if they provided just a date
            if 'T' not in end_date:
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            # Fallback
            end_dt = timezone.now()
            start_dt = end_dt - datetime.timedelta(days=7)
            
        date_range_str = f"{start_dt.strftime('%b %d, %Y')} - {end_dt.strftime('%b %d, %Y')}"
        username = str(user.short_name) if hasattr(user, 'short_name') else str(user)
        
        headers = []
        rows = []
        
        # 2. Extract Data based on type
        settled = Order.objects.filter(
            tenant_id=tenant_id, 
            status=OrderStatus.SETTLED, 
            opened_at__gte=start_dt, 
            opened_at__lte=end_dt
        )
        
        if report_type == "sales":
            headers = ['Date', 'Orders', 'Gross Sales', 'Discounts', 'Taxes', 'Net Sales']
            daily_data = settled.annotate(date=TruncDate('opened_at')).values('date').annotate(
                order_count=Count('id'), gross=Sum('subtotal'), disc=Sum('discount_amount'),
                tax=Sum('tax_amount'), net=Sum('total')
            ).order_by('-date')
            rows = [[d['date'].strftime('%Y-%m-%d') if d['date'] else 'N/A', d['order_count'], float(d['gross'] or 0), float(d['disc'] or 0), float(d['tax'] or 0), float(d['net'] or 0)] for d in daily_data]
            
        elif report_type == "items" or report_type == "product":
            headers = ['Item Name', 'SKU', 'Category', 'Quantity Sold', 'Revenue', 'Cost', 'Profit', 'Current Stock', 'Avg Selling Price']
            items = OrderItem.objects.filter(order__in=settled)
            item_stats = list(items.values('name_snapshot', 'product_id').annotate(
                qty_sold=Sum('qty'),
                revenue=Sum('line_total')
            ).order_by('-qty_sold'))
            
            product_ids = [i['product_id'] for i in item_stats]
            products = Product.objects.filter(id__in=product_ids).select_related('category')
            inventory_items = InventoryItem.objects.filter(product_id__in=product_ids)
            
            prod_cost_map = {i.product_id: i.average_cost for i in inventory_items}
            prod_stock_map = {i.product_id: i.quantity_on_hand for i in inventory_items}
            prod_cat_map = {p.id: p.category.name if p.category else 'Other' for p in products}
            prod_sku_map = {p.id: p.sku for p in products}
            
            for i in item_stats:
                p_id = i['product_id']
                qty = i['qty_sold'] or Decimal('0')
                rev = i['revenue'] or Decimal('0')
                cost = prod_cost_map.get(p_id, Decimal('0'))
                total_cost = qty * cost
                profit = rev - total_cost
                stock = prod_stock_map.get(p_id, Decimal('0'))
                avg_price = rev / qty if qty > 0 else Decimal('0')
                
                rows.append([
                    i['name_snapshot'],
                    prod_sku_map.get(p_id, 'N/A'),
                    prod_cat_map.get(p_id, 'Other'),
                    float(qty), float(rev), float(total_cost), float(profit), float(stock), float(avg_price)
                ])

        elif report_type == "inventory":
            headers = ['SKU', 'Product', 'Warehouse', 'Available Stock', 'Reserved Stock', 'Min Stock', 'Unit Cost', 'Inventory Value']
            items_with_val = InventoryItem.objects.filter(tenant_id=tenant_id, is_active=True).select_related('warehouse').annotate(
                total_value=ExpressionWrapper(F('quantity_on_hand') * F('average_cost'), output_field=DecimalField(max_digits=12, decimal_places=2))
            ).order_by('product_name')
            
            for i in items_with_val:
                rows.append([
                    i.product_sku, i.product_name, i.warehouse.name if i.warehouse else 'Default',
                    float(i.quantity_on_hand), float(i.quantity_reserved), float(i.minimum_stock), 
                    float(i.average_cost), float(i.total_value or 0)
                ])
                
        elif report_type == "tax" or report_type == "gst":
            headers = ['Tax Rate', 'Total Quantity', 'Taxable Value', 'Total CGST', 'Total SGST', 'Total IGST', 'Total Cess']
            # Rely on the GST Filing Service 
            summary = GSTFilingService.get_hsn_summary(start_dt.date(), end_dt.date())
            for entry in summary:
                rows.append([
                    float(entry.get('tax_percentage') or 0),
                    float(entry.get('total_quantity') or 0),
                    float(entry.get('total_taxable_value') or 0),
                    float(entry.get('total_cgst') or 0),
                    float(entry.get('total_sgst') or 0),
                    float(entry.get('total_igst') or 0),
                    float(entry.get('total_cess') or 0)
                ])
                
        elif report_type == "customer":
            headers = ['Customer Phone', 'Name', 'Orders', 'Total Spent']
            customer_data = settled.exclude(customer_phone="").values('customer_phone', 'customer_name').annotate(
                order_count=Count('id'), total=Sum('total')
            ).order_by('-total')
            for d in customer_data:
                rows.append([d['customer_phone'], d['customer_name'] or 'Unknown', d['order_count'], float(d['total'] or 0)])

        elif report_type == "financial" or report_type == "dashboard":
            headers = ['Metric', 'Value']
            rev = settled.aggregate(sum=Sum('total'))['sum'] or Decimal('0')
            disc = settled.aggregate(sum=Sum('discount_amount'))['sum'] or Decimal('0')
            orders = settled.count()
            refunds = Payment.objects.filter(order__tenant_id=tenant_id, kind=PaymentKind.REFUND, status=PaymentStatus.CAPTURED, captured_at__gte=start_dt, captured_at__lte=end_dt).aggregate(sum=Sum('amount'))['sum'] or Decimal('0')
            
            rows = [
                ['Total Revenue', float(rev)],
                ['Total Orders', orders],
                ['Total Discounts Given', float(disc)],
                ['Total Refunds', float(refunds)]
            ]
            
        elif report_type == "staff":
            headers = ['Staff ID', 'Orders Processed', 'Revenue Generated']
            staff_data = settled.values('created_by').annotate(
                order_count=Count('id'), rev=Sum('total')
            ).order_by('-rev')
            for d in staff_data:
                rows.append([str(d['created_by']) or 'System', d['order_count'], float(d['rev'] or 0)])
                
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
            
        title = f"{report_type}_report"
        
        # 3. Route to Format Service
        if export_format == "pdf":
            return PDFExportService.generate(title, headers, rows, date_range_str, username)
        elif export_format == "excel" or export_format == "xlsx":
            return ExcelExportService.generate(title, headers, rows)
        else: # csv
            return CSVExportService.generate(title, headers, rows)
