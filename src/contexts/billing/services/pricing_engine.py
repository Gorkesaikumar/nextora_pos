"""Pricing Engine service for dynamic subscription calculations."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
from django.utils import timezone
from contexts.billing.models.pricing_overrides import (
    TenantPriceOverride,
    SubscriptionDiscount,
    SubscriptionCoupon,
)
from contexts.billing.models import Plan
from contexts.billing.domain.enums import DiscountType


class PricingEngine:
    """Calculates effective subscription pricing with hierarchy:
    1. Tenant Price Override (e.g. Free or ₹499 custom override)
    2. Active Subscription Discounts (Plan/Tenant/Platform level)
    3. Applied Coupon Code
    4. GST / Tax calculation
    """

    @classmethod
    def get_plan_price(cls, plan: Plan) -> Decimal:
        """Return base exact price for a plan."""
        return plan.effective_price

    @classmethod
    def validate_coupon(
        cls, coupon_code: str, tenant: Any = None, plan: Optional[Plan] = None
    ) -> tuple[bool, str, Optional[SubscriptionCoupon]]:
        """Validate coupon code for tenant and plan."""
        if not coupon_code or not coupon_code.strip():
            return False, "No coupon code provided.", None
        coupon = SubscriptionCoupon.objects.filter(code__iexact=coupon_code.strip()).first()
        if not coupon:
            return False, "Invalid coupon code.", None
        is_valid, msg = coupon.is_valid_now()
        if not is_valid:
            return False, msg, coupon
        if plan and coupon.applicable_plans.exists() and not coupon.applicable_plans.filter(id=plan.id).exists():
            return False, f"Coupon is not valid for {plan.name}.", coupon
        if tenant and getattr(tenant, "id", None) and coupon.usages.filter(tenant=tenant).count() >= coupon.per_user_limit:
            return False, "You have already used this coupon maximum times.", coupon
        return True, "Valid", coupon

    @classmethod
    def calculate_effective_price(
        cls,
        tenant: Any,
        plan: Plan,
        coupon_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return full pricing breakdown.

        Returns:
            {
                "base_price": Decimal,
                "override_applied": bool,
                "discount_amount": Decimal,
                "coupon_discount": Decimal,
                "effective_before_tax": Decimal,
                "gst_percentage": Decimal,
                "gst_amount": Decimal,
                "total_amount": Decimal,
                "currency": str,
                "coupon_valid": bool,
                "coupon_error": str,
                "applied_coupon_obj": Optional[SubscriptionCoupon]
            }
        """
        now = timezone.now()
        currency = plan.currency or "INR"
        base_price = plan.effective_price

        # 1. Check Tenant Price Override
        override_applied = False
        if tenant and getattr(tenant, "id", None):
            override = TenantPriceOverride.objects.filter(
                tenant=tenant, plan=plan, is_active=True
            ).first()
            if override and override.is_valid_now():
                override_applied = True
                if override.is_free:
                    base_price = Decimal("0.00")
                else:
                    base_price = override.custom_price

        current_price = base_price
        discount_amount = Decimal("0.00")

        # 2. Check Subscription Discounts (if not already ₹0 / free override)
        if current_price > 0 and not override_applied:
            # Check tenant-specific discount first, then plan-specific, then platform
            discounts = SubscriptionDiscount.objects.filter(is_active=True)
            applicable_discount = None
            for disc in discounts:
                if disc.is_valid_for(tenant=tenant, plan=plan):
                    applicable_discount = disc
                    break

            if applicable_discount:
                if applicable_discount.discount_type == DiscountType.PERCENTAGE:
                    discount_amount = (current_price * applicable_discount.value / Decimal("100.00")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    discount_amount = min(current_price, applicable_discount.value)
                current_price = max(Decimal("0.00"), current_price - discount_amount)

        # 3. Apply Coupon if provided
        coupon_discount = Decimal("0.00")
        coupon_valid = False
        coupon_error = ""
        applied_coupon_obj = None

        if coupon_code and coupon_code.strip() and current_price > 0:
            coupon = SubscriptionCoupon.objects.filter(
                code__iexact=coupon_code.strip()
            ).first()
            if not coupon:
                coupon_error = "Invalid coupon code."
            else:
                is_valid, msg = coupon.is_valid_now()
                if not is_valid:
                    coupon_error = msg
                else:
                    # Check if applicable to this plan
                    if coupon.applicable_plans.exists() and not coupon.applicable_plans.filter(id=plan.id).exists():
                        coupon_error = f"Coupon is not valid for {plan.name}."
                    # Check per-user limit
                    elif tenant and getattr(tenant, "id", None) and coupon.usages.filter(tenant=tenant).count() >= coupon.per_user_limit:
                        coupon_error = "You have already used this coupon maximum times."
                    else:
                        coupon_valid = True
                        applied_coupon_obj = coupon
                        if coupon.discount_type == DiscountType.PERCENTAGE:
                            coupon_discount = (current_price * coupon.value / Decimal("100.00")).quantize(
                                Decimal("0.01"), rounding=ROUND_HALF_UP
                            )
                        else:
                            coupon_discount = min(current_price, coupon.value)
                        current_price = max(Decimal("0.00"), current_price - coupon_discount)

        # 4. Calculate GST / Tax
        gst_pct = Decimal(str(plan.gst_percentage or "18.00"))
        gst_amount = (current_price * gst_pct / Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_amount = (current_price + gst_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "base_price": base_price,
            "override_applied": override_applied,
            "discount_amount": discount_amount,
            "coupon_discount": coupon_discount,
            "effective_before_tax": current_price,
            "gst_percentage": gst_pct,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "currency": currency,
            "coupon_valid": coupon_valid,
            "coupon_error": coupon_error,
            "applied_coupon_obj": applied_coupon_obj,
        }
