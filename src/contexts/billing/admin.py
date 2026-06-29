from django.contrib import admin

from .models import (
    Plan,
    PlanPrice,
    Subscription,
    SubscriptionInvoice,
    SubscriptionPayment,
    UsageCounter,
    WebhookEvent,
)


class PlanPriceInline(admin.TabularInline):
    model = PlanPrice
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "trial_days", "grace_days", "is_active"]
    list_filter = ["is_active", "is_public"]
    search_fields = ["code", "name"]
    inlines = [PlanPriceInline]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "plan", "interval", "status",
                    "current_period_end", "auto_renew"]
    list_filter = ["status", "interval"]


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "tenant", "total", "status", "due_at", "paid_at"]
    list_filter = ["status"]
    search_fields = ["number"]


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ["invoice", "amount", "status", "provider", "captured_at"]
    list_filter = ["status", "provider"]


@admin.register(UsageCounter)
class UsageCounterAdmin(admin.ModelAdmin):
    list_display = ["tenant", "metric", "period_key", "value"]
    list_filter = ["metric"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["provider", "event_type", "event_id", "status", "processed_at"]
    list_filter = ["provider", "status"]
    search_fields = ["event_id"]
