from django.contrib import admin

from .models import KOT, Invoice, Order, OrderItem, Payment


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
