"""Restaurant Django Admin."""
from django.contrib import admin

from .models import (
    Branch,
    BranchGSTProfile,
    BranchSettings,
    BusinessHours,
    CashCounter,
    DiningTable,
    Holiday,
    KitchenStation,
    Printer,
    Restaurant,
)


class BranchGSTProfileInline(admin.StackedInline):
    model = BranchGSTProfile
    extra = 0
    readonly_fields = ["state_code", "pan"]


class BranchSettingsInline(admin.StackedInline):
    model = BranchSettings
    extra = 0


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


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "restaurant", "status", "city", "country", "is_active"]
    list_filter = ["status", "country", "is_active"]
    search_fields = ["name", "code", "city"]
    readonly_fields = ["status"]
    inlines = [BranchGSTProfileInline, BranchSettingsInline, BusinessHoursInline, HolidayInline]


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ["number", "branch", "capacity", "status", "shape", "is_active"]
    list_filter = ["branch", "status", "shape", "is_active"]
    search_fields = ["number"]
    readonly_fields = ["status", "merge_group", "qr_code_url"]


@admin.register(KitchenStation)
class KitchenStationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "branch", "kind", "sort_order", "is_active"]
    list_filter = ["branch", "kind", "is_active"]
    search_fields = ["name", "code"]


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "branch", "kind", "station", "is_active"]
    list_filter = ["branch", "kind", "is_active"]
    search_fields = ["name", "code"]


@admin.register(CashCounter)
class CashCounterAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "branch", "is_active"]
    list_filter = ["branch", "is_active"]
    search_fields = ["name", "code"]
