"""Comprehensive test suite for Nextora POS Dynamic Subscription & License Management Architecture."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from contexts.billing.domain.enums import BillingInterval, DiscountScope, DiscountType, SubscriptionStatus
from contexts.billing.models import (
    GlobalTrialConfig,
    Plan,
    Subscription,
    SubscriptionCoupon,
    SubscriptionDiscount,
    SubscriptionVisibilityConfig,
    TenantPriceOverride,
)
from contexts.billing.models.plan import PlanPrice
from contexts.billing.services.license_service import LicenseService
from contexts.billing.services.pricing_engine import PricingEngine
from contexts.tenants.models import Tenant
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.mark.django_db
class TestPricingEngine:
    """Test dynamic price calculations, interval lookups, overrides, coupons, and discounts."""

    def test_interval_exact_price_lookups(self):
        plan = Plan.objects.create(
            code="pro-dynamic",
            name="Professional Dynamic",
            original_price=Decimal("1999.00"),
            sale_price=Decimal("1499.00"),
        )
        # Create exact interval prices
        PlanPrice.objects.create(plan=plan, interval=BillingInterval.DAILY, amount=Decimal("99.00"))
        PlanPrice.objects.create(plan=plan, interval=BillingInterval.WEEKLY, amount=Decimal("499.00"))
        PlanPrice.objects.create(plan=plan, interval=BillingInterval.MONTHLY, amount=Decimal("1499.00"))
        PlanPrice.objects.create(plan=plan, interval=BillingInterval.YEARLY, amount=Decimal("14999.00"))

        assert PricingEngine.get_plan_price(plan, BillingInterval.DAILY) == Decimal("99.00")
        assert PricingEngine.get_plan_price(plan, BillingInterval.WEEKLY) == Decimal("499.00")
        assert PricingEngine.get_plan_price(plan, BillingInterval.MONTHLY) == Decimal("1499.00")
        assert PricingEngine.get_plan_price(plan, BillingInterval.YEARLY) == Decimal("14999.00")

    def test_interval_fallback_auto_calculation(self):
        plan = Plan.objects.create(
            code="basic-fallback",
            name="Basic Fallback",
            original_price=Decimal("1000.00"),
            sale_price=Decimal("1000.00"),
        )
        # Without exact interval overrides, engine should fall back based on sale_price (1000/month)
        # Daily = 1000 / 30 = 33.33
        assert PricingEngine.get_plan_price(plan, BillingInterval.DAILY) == Decimal("33.33")
        # Yearly = 1000 * 12 = 12000.00
        assert PricingEngine.get_plan_price(plan, BillingInterval.YEARLY) == Decimal("12000.00")

    def test_tenant_price_override_precedence(self):
        tenant = Tenant.objects.create(name="VIP Restaurant", slug="vip-rest")
        set_current_tenant(tenant.id)
        try:
            plan = Plan.objects.create(
                code="enterprise",
                name="Enterprise Suite",
                sale_price=Decimal("5000.00"),
            )
            TenantPriceOverride.objects.create(
                tenant=tenant,
                plan=plan,
                custom_price=Decimal("3500.00"),
                is_free=False,
                is_active=True,
            )

            effective = PricingEngine.calculate_effective_price(
                tenant=tenant,
                plan=plan,
                interval=BillingInterval.MONTHLY,
            )
            assert effective["base_price"] == Decimal("3500.00")
            assert effective["override_applied"] is True
        finally:
            clear_current_tenant()

    def test_coupon_and_discount_calculations(self):
        tenant = Tenant.objects.create(name="Discounted Rest", slug="disc-rest")
        set_current_tenant(tenant.id)
        try:
            plan = Plan.objects.create(
                code="standard",
                name="Standard Plan",
                sale_price=Decimal("2000.00"),
            )
            PlanPrice.objects.create(plan=plan, interval=BillingInterval.MONTHLY, amount=Decimal("2000.00"))

            # 1. Test Percentage Coupon (20% off)
            SubscriptionCoupon.objects.create(
                code="SAVE20",
                discount_type=DiscountType.PERCENTAGE,
                value=Decimal("20.00"),
                usage_limit=10,
                is_active=True,
            )
            eff_pct = PricingEngine.calculate_effective_price(
                tenant=tenant, plan=plan, interval=BillingInterval.MONTHLY, coupon_code="SAVE20"
            )
            assert eff_pct["effective_before_tax"] == Decimal("1600.00")
            assert eff_pct["coupon_valid"] is True

            # 2. Test Flat Amount Coupon (₹500 off)
            SubscriptionCoupon.objects.create(
                code="FLAT500",
                discount_type=DiscountType.FLAT,
                value=Decimal("500.00"),
                usage_limit=10,
                is_active=True,
            )
            eff_fixed = PricingEngine.calculate_effective_price(
                tenant=tenant, plan=plan, interval=BillingInterval.MONTHLY, coupon_code="FLAT500"
            )
            assert eff_fixed["effective_before_tax"] == Decimal("1500.00")
            assert eff_fixed["coupon_valid"] is True
        finally:
            clear_current_tenant()

    def test_coupon_validation_and_usage_limits(self):
        SubscriptionCoupon.objects.create(
            code="LIMITED5",
            discount_type=DiscountType.PERCENTAGE,
            value=Decimal("10.00"),
            usage_limit=0,  # Already 0 remaining / reached
            is_active=True,
        )
        is_valid, msg, disc = PricingEngine.validate_coupon("LIMITED5")
        assert not is_valid
        assert "limit reached" in msg


@pytest.mark.django_db
class TestLicenseServiceAndFeatureGuarantee:
    """Test Global Trial configuration, zero-overlap renewals, and 100% Feature Accessibility guarantee."""

    def test_100_percent_feature_accessibility_guarantee(self):
        """Core business rule: Every customer receives 100% of Nextora POS features regardless of plan."""
        plan_daily = Plan.objects.create(
            code="daily-basic", name="Daily Pass", sale_price=Decimal("99.00"), features={"all_pos_features": True}
        )
        plan_yearly = Plan.objects.create(
            code="yearly-pro", name="Yearly Pro", sale_price=Decimal("9999.00"), features={"all_pos_features": True}
        )

        tenant_a = Tenant.objects.create(name="Pop-up Stall", slug="popup")
        tenant_b = Tenant.objects.create(name="Grand Hotel", slug="hotel")

        set_current_tenant(tenant_a.id)
        try:
            sub_a = LicenseService.activate_trial(tenant_a, plan_daily)
            assert sub_a.has_feature("all_pos_features") is True
        finally:
            clear_current_tenant()

        set_current_tenant(tenant_b.id)
        try:
            sub_b = LicenseService.renew_or_upgrade(tenant_b, plan_yearly, interval=BillingInterval.YEARLY)
            assert sub_b.has_feature("all_pos_features") is True
        finally:
            clear_current_tenant()

    def test_global_trial_configuration_and_countdown(self):
        trial_config = GlobalTrialConfig.get_solo()
        trial_config.is_enabled = True
        trial_config.trial_days = 14
        trial_config.grace_days = 5
        trial_config.save()

        plan = Plan.objects.create(
            code="standard-trial", name="Standard", sale_price=Decimal("1200.00"), trial_days=14
        )
        tenant = Tenant.objects.create(name="New Trial Cafe", slug="trial-cafe")

        set_current_tenant(tenant.id)
        try:
            sub = LicenseService.activate_trial(tenant, plan)
            assert sub.status == SubscriptionStatus.TRIALING
            assert sub.has_access() is True

            summary = LicenseService.get_license_summary(tenant)
            assert summary["has_subscription"] is True
            assert summary["status"] == SubscriptionStatus.TRIALING
            assert summary["remaining_days"] in [13, 14]
            assert summary["can_transact"] is True
        finally:
            clear_current_tenant()

    def test_zero_overlap_renewal_and_carryover(self):
        plan = Plan.objects.create(code="renewal-plan", name="Renewal Plan", sale_price=Decimal("1500.00"))
        tenant = Tenant.objects.create(name="Renewing Rest", slug="renew-rest")

        set_current_tenant(tenant.id)
        try:
            now = timezone.now()
            Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                interval=BillingInterval.MONTHLY,
                price_amount=Decimal("1500.00"),
                current_period_start=now - timedelta(days=20),
                current_period_end=now + timedelta(days=10),
            )

            new_sub = LicenseService.renew_or_upgrade(
                tenant=tenant,
                new_plan=plan,
                interval=BillingInterval.MONTHLY,
            )

            days_diff = (new_sub.current_period_end - now).days
            assert days_diff in [39, 40]
            assert new_sub.status == SubscriptionStatus.ACTIVE
            assert new_sub.has_feature("all_pos_features") is True
        finally:
            clear_current_tenant()
