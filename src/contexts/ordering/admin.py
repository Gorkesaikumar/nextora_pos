from django.contrib import admin

from .models import KOT, Invoice, Order, OrderItem, Payment, InvoiceConfiguration, InvoiceSnapshot


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "status", "type", "total", "paid_amount",
                    "due_amount"]
    list_filter = ["status", "type"]
    inlines = [OrderItemInline, PaymentInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "total", "status", "financial_year", "issued_at"]
    list_filter = ["status", "financial_year"]
    search_fields = ["number"]


@admin.register(KOT)
class KOTAdmin(admin.ModelAdmin):
    list_display = ["number", "order", "kitchen_station_id", "status", "printed_at"]
    list_filter = ["status"]


@admin.register(InvoiceConfiguration)
class InvoiceConfigurationAdmin(admin.ModelAdmin):
    list_display = ["tenant", "restaurant_name", "paper_size", "currency_symbol"]
    search_fields = ["tenant__name", "restaurant_name"]
    list_filter = ["paper_size"]


@admin.register(InvoiceSnapshot)
class InvoiceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["invoice", "business_name", "total", "created_at"]
    search_fields = ["business_name", "invoice__number"]
    list_filter = ["paper_size", "created_at"]
    readonly_fields = [
        "invoice", "business_name", "business_address", "business_gstin",
        "business_fssai", "items_snapshot", "subtotal", "total",
        "cgst", "sgst", "igst", "tax_amount", "round_off",
        "payment_methods", "amount_paid", "change_returned",
        "customer_name", "cashier_name", "created_at",
    ]
