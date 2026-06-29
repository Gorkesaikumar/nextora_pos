from django.contrib import admin

from .models import (
    Coupon,
    CouponRedemption,
    CreditLedger,
    Customer,
    LoyaltyProgram,
    PointsLedger,
    WalletTransaction,
)


class PointsLedgerInline(admin.TabularInline):
    model = PointsLedger
    extra = 0
    readonly_fields = ["points", "reason", "order_id", "created_at"]


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ["amount", "tx_type", "order_id", "created_at"]


class CreditLedgerInline(admin.TabularInline):
    model = CreditLedger
    extra = 0
    readonly_fields = ["amount", "ledger_type", "invoice_id", "created_at"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "phone",
        "email",
        "gstin",
        "loyalty_tier",
        "loyalty_points",
        "lifetime_points",
        "wallet_balance",
        "outstanding_credit",
        "accepts_marketing",
    ]
    list_filter = ["loyalty_tier", "accepts_marketing"]
    search_fields = ["name", "phone", "email", "gstin"]
    readonly_fields = ["loyalty_points", "lifetime_points", "wallet_balance", "outstanding_credit"]
    inlines = [PointsLedgerInline, WalletTransactionInline, CreditLedgerInline]


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = [
        "earn_rate", "redeem_value",
        "silver_threshold", "gold_threshold", "platinum_threshold",
        "points_expiry_days",
    ]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "valid_from",
        "valid_to",
        "max_uses",
        "per_customer_limit",
        "current_uses",
        "is_active",
    ]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ["coupon", "customer", "order_id", "created_at"]
    search_fields = ["coupon__code", "customer__phone"]
    readonly_fields = ["coupon", "customer", "order_id", "idempotency_key", "created_at"]
