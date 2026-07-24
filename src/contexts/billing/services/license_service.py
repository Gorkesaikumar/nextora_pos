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
from contexts.billing.services import invoice_service
from contexts.billing.gateways import get_gateway


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

        # For UI purposes, INCOMPLETE is not "expired" even though it lacks access
        if sub.status == SubscriptionStatus.INCOMPLETE:
            is_expired = False

        banner_text = ""
        banner_type = "info"

        if sub.status == SubscriptionStatus.INCOMPLETE:
            banner_text = "Your subscription setup is incomplete. Please complete your payment to activate your plan."
            banner_type = "warning"
        elif sub.status == SubscriptionStatus.TRIALING:
            if is_expired:
                banner_text = "Trial Expired. Please upgrade your plan to continue using Nextora POS."
                banner_type = "expired"
            else:
                if rem_days > 3:
                    banner_text = f"You are currently in the trial period. {rem_days} Days Remaining."
                    banner_type = "info" # UI will render this as green or neutral
                elif rem_days == 3:
                    banner_text = "Your free trial expires in 3 days. Upgrade now to avoid service interruption."
                    banner_type = "warning"
                elif rem_days > 1:
                    banner_text = f"Your free trial expires in {rem_days} days. Upgrade now to avoid service interruption."
                    banner_type = "warning"
                elif rem_days <= 1:
                    banner_text = "Your trial expires today. Upgrade now to continue using Nextora POS."
                    banner_type = "danger"
        elif is_expired:
            banner_text = "Your subscription has expired. Please renew your plan to continue using Nextora POS."
            banner_type = "expired"
        elif sub.in_grace:
            banner_text = f"Your subscription is past due. Grace period active for {rem_days} more day(s)."
            banner_type = "danger"
        else:
            from contexts.billing.domain.enums import BillingInterval
            
            reminder_threshold = 7
            warning_threshold = 3
            urgent_threshold = 1
            
            # Adaptive thresholds so short-term plans also disappear after purchase
            if getattr(sub, 'interval', None) == BillingInterval.DAILY:
                reminder_threshold = 0
                warning_threshold = -1
                urgent_threshold = 0
            elif getattr(sub, 'interval', None) == BillingInterval.WEEKLY:
                reminder_threshold = 2
                warning_threshold = 1
                urgent_threshold = 0
            elif getattr(sub, 'interval', None) == BillingInterval.MONTHLY:
                reminder_threshold = 5

            if rem_days > reminder_threshold:
                banner_type = "hidden"
                banner_text = ""
            elif rem_days <= urgent_threshold:
                banner_text = f"URGENT: Your {sub.plan.name} expires today! Renew now." if rem_days == 0 else f"URGENT: Your {sub.plan.name} expires in {rem_days} day(s)! Renew now."
                banner_type = "danger"
            elif rem_days <= warning_threshold:
                banner_text = f"Action Required: Your {sub.plan.name} expires in {rem_days} day(s)."
                banner_type = "warning"
            else:
                banner_text = f"Reminder: Your {sub.plan.name} expires in {rem_days} day(s)."
                banner_type = "info"

        return {
            "has_subscription": True,
            "status": sub.status,
            "is_expired": is_expired,
            "can_transact": not is_expired,
            "plan_name": sub.plan.name,
            "plan_code": sub.plan.code,
            "remaining_days": rem_days,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
            "trial_end": sub.trial_end,
            "interval": sub.interval,
            "provider_subscription_id": sub.provider_subscription_id,
            "last_payment_date": sub.current_period_start,
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
    def create_checkout_session(
        cls,
        tenant: Any,
        new_plan: Plan,
        interval: str = "monthly",
        coupon_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate a Razorpay Order and INCOMPLETE Subscription for checkout."""
        now = timezone.now()
        current_sub = Subscription.objects.filter(tenant=tenant).order_by("-created_at").first()

        interval_days_map = {
            BillingInterval.DAILY: 1, BillingInterval.WEEKLY: 7, BillingInterval.MONTHLY: 30,
            BillingInterval.QUARTERLY: 90, BillingInterval.HALF_YEARLY: 180,
            BillingInterval.YEARLY: 365, BillingInterval.CUSTOM: new_plan.duration_days or 30,
        }
        duration_days = interval_days_map.get(interval, 30)

        pricing = PricingEngine.calculate_effective_price(
            tenant=tenant, plan=new_plan, coupon_code=coupon_code
        )

        start_time = now
        if current_sub and not current_sub.is_expired(now=now):
            start_time = max(now, current_sub.current_period_end)

        end_time = start_time + timedelta(days=duration_days)
        grace_until = end_time + timedelta(days=new_plan.grace_days or 7)
        renewal_count = (current_sub.renewal_count + 1) if current_sub else 1

        # NOTE: We DO NOT expire the current subscription yet. It remains active until payment succeeds.
        new_sub = Subscription.objects.create(
            tenant=tenant,
            plan=new_plan,
            interval=interval,
            price_amount=pricing["total_amount"],
            currency=pricing["currency"],
            status=SubscriptionStatus.INCOMPLETE,
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

        # Generate invoice
        invoice = invoice_service.generate_invoice(
            tenant_id=tenant.id,
            subscription=new_sub,
            period_start=start_time,
            period_end=end_time,
            now=now,
        )

        amount_minor = int(pricing["total_amount"] * 100)
        gateway = get_gateway()
        order = gateway.create_order(
            amount_minor=amount_minor,
            currency=pricing["currency"],
            receipt=invoice.number,
            notes={"tenant_id": str(tenant.id), "plan": new_plan.code}
        )

        invoice.provider_order_id = order.id
        invoice.save(update_fields=["provider_order_id", "updated_at"])

        return {
            "order_id": order.id,
            "amount_minor": order.amount_minor,
            "currency": order.currency,
            "invoice_number": invoice.number,
        }

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
