from django.contrib import admin

from .models import (
    Branch,
    CashCounter,
    Holiday,
    Table,
    Tenant,
    TenantConfiguration,
    TenantDomain,
)


class TenantDomainInline(admin.TabularInline):
    model = TenantDomain
    extra = 0


class TenantConfigurationInline(admin.StackedInline):
    model = TenantConfiguration
    extra = 1
    max_num = 1
    can_delete = False


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "status", "base_currency", "created_at"]
    list_filter = ["status"]
    search_fields = ["slug", "name", "legal_name"]
    inlines = [TenantDomainInline, TenantConfigurationInline]


@admin.register(TenantConfiguration)
class TenantConfigurationAdmin(admin.ModelAdmin):
    list_display = ["tenant", "gst_number", "currency", "timezone"]
    search_fields = ["tenant__slug", "tenant__name", "gst_number"]





class CashCounterInline(admin.TabularInline):
    model = CashCounter
    extra = 0


class HolidayInline(admin.TabularInline):
    model = Holiday
    extra = 0


class TableInline(admin.TabularInline):
    model = Table
    extra = 0


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "tenant", "phone", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "phone"]
    inlines = [CashCounterInline, HolidayInline]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ["number", "branch", "capacity", "status", "qr_code_url"]
    list_filter = ["status", "branch"]
    search_fields = ["number", "branch__name"]
    actions = ["generate_qr_codes"]

    @admin.action(description="Generate/Refresh QR Codes for selected tables")
    def generate_qr_codes(self, request, queryset):
        from .services import generate_table_qr
        success_count = 0
        for table in queryset:
            try:
                generate_table_qr(table.id)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"Failed to generate QR for Table {table.number}: {e}", level="error")
        self.message_user(request, f"Generated {success_count} table QR codes.")


@admin.register(CashCounter)
class CashCounterAdmin(admin.ModelAdmin):
    list_display = ["name", "branch", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "branch__name"]


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "branch", "date"]
    list_filter = ["date"]
    search_fields = ["name", "branch__name"]
