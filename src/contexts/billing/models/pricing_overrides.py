"""Customer-Specific Pricing Overrides, Discounts, and Coupons models."""
from decimal import Decimal
from django.db import models
from django.utils import timezone
from shared.infrastructure.models.base import TimeStampedModel, UUIDModel
from shared.tenancy.models import TenantAwareModel
from contexts.billing.domain.enums import DiscountScope, DiscountType, CouponEligibility


class TenantPriceOverride(UUIDModel, TimeStampedModel):
    """Overrides subscription pricing for a specific tenant and plan."""
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="price_overrides"
    )
    plan = models.ForeignKey(
        "billing.Plan", on_delete=models.CASCADE, related_name="tenant_overrides"
    )
    custom_price = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    is_free = models.BooleanField(
        default=False, help_text="If checked, tenant gets this plan for ₹0/Free."
    )
    reason = models.CharField(max_length=255, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tenant_price_override"
        unique_together = ["tenant", "plan"]

    def __str__(self) -> str:
        return f"Override for {self.tenant_id} on {self.plan.code}: ₹{self.custom_price} (Free: {self.is_free})"

    def is_valid_now(self) -> bool:
        if not self.is_active:
            return False
        if self.valid_until and self.valid_until < timezone.now():
            return False
        return True


class SubscriptionDiscount(UUIDModel, TimeStampedModel):
    """Platform or Tenant specific promotional discounts."""
    name = models.CharField(max_length=100)
    discount_type = models.CharField(
        max_length=16, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    value = models.DecimalField(max_digits=14, decimal_places=2)
    scope = models.CharField(
        max_length=16, choices=DiscountScope.choices, default=DiscountScope.PLATFORM
    )
    target_tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="discounts"
    )
    target_plan = models.ForeignKey(
        "billing.Plan", null=True, blank=True, on_delete=models.CASCADE, related_name="discounts"
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_discount"

    def __str__(self) -> str:
        return f"Discount {self.name} ({self.value} {self.discount_type})"

    def is_valid_for(self, tenant=None, plan=None) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.scope == DiscountScope.TENANT and self.target_tenant_id and tenant and self.target_tenant_id != tenant.id:
            return False
        if self.scope == DiscountScope.PLAN and self.target_plan_id and plan and self.target_plan_id != plan.id:
            return False
        return True


class SubscriptionCoupon(UUIDModel, TimeStampedModel):
    """Coupon codes applicable at checkout or renewal."""
    name = models.CharField(max_length=100, default="Untitled Coupon")
    description = models.TextField(blank=True, help_text="Public description (e.g. '50% off for Grand Opening')")
    internal_notes = models.TextField(blank=True, help_text="Private notes for Super Admin")
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_type = models.CharField(
        max_length=16, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    value = models.DecimalField(max_digits=14, decimal_places=2)
    minimum_purchase_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, help_text="Minimum cart value required"
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, help_text="Cap for percentage discounts"
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total maximum redemptions across all users."
    )
    per_user_limit = models.PositiveIntegerField(
        default=1, help_text="Maximum times a single tenant can apply this coupon."
    )
    applicable_plans = models.ManyToManyField(
        "billing.Plan", blank=True, related_name="coupons"
    )
    eligibility = models.CharField(
        max_length=32, choices=CouponEligibility.choices, default=CouponEligibility.ALL
    )
    is_active = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        db_table = "subscription_coupon"

    def __str__(self) -> str:
        return f"Coupon {self.code} ({self.value} {self.discount_type})"

    def is_valid_now(self, cart_amount: Decimal = None, tenant_status: str = None) -> tuple[bool, str]:
        if not self.is_active:
            return False, "Coupon is inactive."
        now = timezone.now()
        if self.valid_from and self.valid_from > now:
            return False, "Coupon is not yet active."
        if self.valid_until and self.valid_until < now:
            return False, "Coupon has expired."
        if self.usage_limit is not None:
            if self.usages.count() >= self.usage_limit:
                return False, "Coupon usage limit reached."
        if self.minimum_purchase_amount and cart_amount is not None:
            if cart_amount < self.minimum_purchase_amount:
                return False, f"Minimum purchase of ₹{self.minimum_purchase_amount} required."
                
        # Eligibility Checks
        if self.eligibility == CouponEligibility.NEW_ONLY and tenant_status == 'existing':
            return False, "This coupon is valid for new customers only."
        elif self.eligibility == CouponEligibility.EXISTING and tenant_status == 'new':
            return False, "This coupon is valid for existing customers only."
            
        return True, "Valid"


class CouponUsage(UUIDModel, TimeStampedModel):
    """Audit record of a coupon applied to a tenant subscription."""
    coupon = models.ForeignKey(
        SubscriptionCoupon, on_delete=models.CASCADE, related_name="usages"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="coupon_usages"
    )
    subscription = models.ForeignKey(
        "billing.Subscription", null=True, blank=True, on_delete=models.SET_NULL, related_name="coupon_usages"
    )
    used_at = models.DateTimeField(default=timezone.now)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "coupon_usage"

    def __str__(self) -> str:
        return f"{self.coupon.code} used by {self.tenant_id}"
