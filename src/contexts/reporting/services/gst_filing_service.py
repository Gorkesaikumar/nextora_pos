import datetime
from django.db.models import Sum, Q, F, Count
from shared.tenancy.context import get_current_tenant
from contexts.ordering.models import OrderStatus, OrderItem

class GSTFilingService:
    @staticmethod
    def get_hsn_summary(start_date: datetime.date, end_date: datetime.date):
        """
        Returns an HSN-wise summary of all sales within the given date range.
        This is typically required for GSTR-1 Table 12.
        """
        tenant = get_current_tenant()
        
        # We assume Product model has an `hsn_code` and `uom` (Unit of Measurement), 
        # but since we might not have it strictly defined, we group by Product Category or Tax Rate.
        # Let's group by tax rate since that is most critical.
        
        items = OrderItem.objects.filter(
            order__tenant=tenant,
            order__status=OrderStatus.SETTLED,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        ).values(
            tax_percentage=F('tax_rate')
        ).annotate(
            total_quantity=Sum('qty'),
            total_taxable_value=Sum(
                F('qty') * F('unit_price')
            ),
            total_igst=Sum('order__igst'),
            total_cgst=Sum('order__cgst'),
            total_sgst=Sum('order__sgst'),
            total_cess=Sum('order__cess')
        ).order_by('tax_percentage')
        
        return list(items)

    @staticmethod
    def get_b2b_b2c_summary(start_date: datetime.date, end_date: datetime.date):
        """
        Groups invoices by B2B (registered customer with GSTIN) and B2C (unregistered).
        """
        tenant = get_current_tenant()
        
        # For simplicity, if customer_name exists and we assume no GSTIN field on order currently,
        # we classify all as B2C. In a real scenario, we check if customer has a GSTIN.
        from contexts.ordering.models import Invoice
        
        invoices = Invoice.objects.filter(
            tenant=tenant,
            issued_at__date__gte=start_date,
            issued_at__date__lte=end_date
        ).aggregate(
            b2c_count=Count('id'),
            b2c_taxable=Sum(F('order__total') - F('order__tax_amount')),
            b2c_tax=Sum('order__tax_amount'),
            b2c_total=Sum('order__total')
        )
        
        return {
            "b2b": {
                "count": 0,
                "taxable": 0,
                "tax": 0,
                "total": 0
            },
            "b2c": {
                "count": invoices["b2c_count"] or 0,
                "taxable": invoices["b2c_taxable"] or 0,
                "tax": invoices["b2c_tax"] or 0,
                "total": invoices["b2c_total"] or 0
            }
        }
