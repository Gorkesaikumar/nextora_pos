"""License Service for dynamic trial management and subscription renewals."""
from datetime import timedelta
from typing import Any, Optional
from django.db import transaction
from django.utils import timezone
from contexts.billing.models import (
    Plan,
    Subscription,
    GlobalTrialConfig,
    SubscriptionVisibilityConfig,
)
from contexts.billing.models.pricing_overrides import CouponUsage
from contexts.billing.domain.enums import SubscriptionStatus, BillingInterval
from contexts.billing.services.pricing_engine import PricingEngine


class LicenseService:
    """Centralized service for trial status, banner generation, and renewals."""

    @classmethod
    def get_license_summary(cls, tenant: Any) -> dict[str, Any]:
        """Return comprehensive license & trial summary for the tenant dashboard."""
        now = timezone.now()
        trial_config = GlobalTrialConfig.get_solo()
        visibility_config = SubscriptionVisibilityConfig.get_solo()

        sub = Subscription.objects.filter(tenant=tenant).order_by("-created_at").first()

        if not sub:
            return {
                "has_subscription": False,
                "status": "none",
                "is_expired": True,
                "can_transact": False,
                "plan_name": "No Plan",
                "remaining_days": 0,
                "banner_text": trial_config.expired_message,
                "banner_type": "expired",
                "visible_intervals": visibility_config.get_visible_intervals(),
            }

        rem_days = sub.remaining_days(now=now)
        is_expired = sub.is_expired(now=now)

        banner_text = ""
        banner_type = "info"

        if sub.status == SubscriptionStatus.TRIALING:
            if is_expired:
                banner_text = trial_config.expired_message
                banner_type = "expired"
            else:
                # Format countdown banner ("Free Trial — {days} Days Remaining...")
                tpl = trial_config.banner_message or "Free Trial — {days} Days Remaining. Upgrade before your trial expires."
                banner_text = tpl.replace("{days}", str(rem_days))
                if rem_days <= trial_config.reminder_days_before:
                    banner_type = "warning"
                else:
                    banner_type = "info"
        elif is_expired:
            banner_text = "Your subscription has expired. Please renew your plan to continue using Nextora POS."
            banner_type = "expired"
        elif sub.in_grace:
            banner_text = f"Your subscription is past due. Grace period active for {rem_days} more day(s)."
            banner_type = "warning"
        elif rem_days <= 7:
            banner_text = f"Your {sub.plan.name} subscription expires in {rem_days} day(s). Renew now to avoid interruption."
            banner_type = "warning"

        return {
            "has_subscription": True,
            "status": sub.status,
            "is_expired": is_expired,
            "can_transact": not is_expired,
            "plan_name": sub.plan.name,
            "plan_code": sub.plan.code,
            "remaining_days": rem_days,
            "current_period_end": sub.current_period_end,
            "banner_text": banner_text,
            "banner_type": banner_type,
            "visible_intervals": visibility_config.get_visible_intervals(),
            "subscription": sub,
        }

    @classmethod
    def check_transaction_access(cls, tenant: Any) -> tuple[bool, str]:
        """Check if tenant can create orders, complete payments, or print bills.

        Returns:
            (allowed: bool, reason: str)
        """
        if not tenant:
            return False, "No active workspace selected."
        summary = cls.get_license_summary(tenant)
        if not summary["can_transact"]:
            return False, summary["banner_text"] or "License expired."
        return True, "Valid"

    @classmethod
    @transaction.atomic
    def activate_trial(cls, tenant: Any, plan: Optional[Plan] = None) -> Subscription:
        """Provision automatic free trial for a newly registered tenant."""
        now = timezone.now()
        trial_config = GlobalTrialConfig.get_solo()

        if not plan:
            plan = Plan.objects.filter(is_active=True, is_default=True).first()
            if not plan:
                plan = Plan.objects.filter(is_active=True).first()

        trial_days = trial_config.trial_days if trial_config.is_enabled else 0
        if plan and plan.trial_days > 0:
            trial_days = plan.trial_days

        trial_end = now + timedelta(days=trial_days)
        grace_until = trial_end + timedelta(days=trial_config.grace_days)

        # Deactivate any previous live subs
        Subscription.objects.filter(tenant=tenant, status__in=SubscriptionStatus.occupied()).update(
            status=SubscriptionStatus.EXPIRED
        )

        sub = Subscription.objects.create(
            tenant=tenant,
            plan=plan,
            interval=BillingInterval.MONTHLY,
            price_amount=0,
            currency=plan.currency if plan else "INR",
            status=SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=trial_end,
            trial_end=trial_end,
            grace_until=grace_until,
            auto_renew=False,
            renewal_count=0,
        )
        return sub

    @classmethod
    @transaction.atomic
    def renew_or_upgrade(
        cls,
        tenant: Any,
        new_plan: Plan,
        interval: str = "monthly",
        coupon_code: Optional[str] = None,
    ) -> Subscription:
        """Upgrade or renew subscription with zero overlap / loss of purchased time."""
        now = timezone.now()
        current_sub = Subscription.objects.filter(tenant=tenant).order_by("-created_at").first()

        # Calculate duration in days for interval
        interval_days_map = {
            BillingInterval.DAILY: 1,
            BillingInterval.WEEKLY: 7,
            BillingInterval.MONTHLY: 30,
            BillingInterval.QUARTERLY: 90,
            BillingInterval.HALF_YEARLY: 180,
            BillingInterval.YEARLY: 365,
            BillingInterval.CUSTOM: new_plan.duration_days or 30,
        }
        duration_days = interval_days_map.get(interval, 30)

        # Calculate pricing
        pricing = PricingEngine.calculate_effective_price(
            tenant=tenant, plan=new_plan, interval=interval, coupon_code=coupon_code
        )

        # Determine start and end date (zero overlap policy)
        start_time = now
        if current_sub and not current_sub.is_expired(now=now):
            # If current sub is still active or trialing, extend from current_period_end if future
            start_time = max(now, current_sub.current_period_end)

        end_time = start_time + timedelta(days=duration_days)
        grace_until = end_time + timedelta(days=new_plan.grace_days or 7)

        renewal_count = (current_sub.renewal_count + 1) if current_sub else 1

        # Deactivate previous live subscription if any
        if current_sub and current_sub.status in SubscriptionStatus.occupied():
            current_sub.status = SubscriptionStatus.EXPIRED
            current_sub.save(update_fields=["status"])

        new_sub = Subscription.objects.create(
            tenant=tenant,
            plan=new_plan,
            interval=interval,
            price_amount=pricing["total_amount"],
            currency=pricing["currency"],
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=end_time,
            grace_until=grace_until,
            auto_renew=True,
            renewal_count=renewal_count,
            applied_coupon_code=pricing["applied_coupon_obj"].code if pricing["applied_coupon_obj"] else "",
        )

        if pricing["applied_coupon_obj"]:
            CouponUsage.objects.create(
                coupon=pricing["applied_coupon_obj"],
                tenant=tenant,
                subscription=new_sub,
                discount_amount=pricing["coupon_discount"],
            )

        return new_sub
