"""Restaurant Django Admin."""
from django.contrib import admin

from .models import (
    BusinessHours,
    CashCounter,
    DiningTable,
    Holiday,
    KitchenStation,
    Printer,
    Restaurant,
)


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 0


class HolidayInline(admin.TabularInline):
    model = Holiday
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "is_default", "created_at"]
    list_filter = ["status", "is_default"]
    search_fields = ["name", "slug"]
    readonly_fields = ["slug", "status"]


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ["number", "capacity", "status", "shape", "is_active"]
    list_filter = ["status", "shape", "is_active"]
    search_fields = ["number"]
    readonly_fields = ["status", "merge_group", "qr_code_url"]


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "kind", "sort_order", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "code"]


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "kind", "station", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "code"]


@admin.register(CashCounter)
class CashCounterAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
