"""Super Admin views for complete SaaS Subscription & License management."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from contexts.billing.models import (
    GlobalTrialConfig,
    Plan,
    SubscriptionCoupon,
    SubscriptionDiscount,
    SubscriptionVisibilityConfig,
)
from contexts.billing.domain.enums import BillingInterval
from contexts.super_admin.mixins import SuperAdminRequiredMixin

# Duration type → default days mapping
DURATION_DAYS_MAP = {
    BillingInterval.DAILY: 1,
    BillingInterval.WEEKLY: 7,
    BillingInterval.MONTHLY: 30,
    BillingInterval.QUARTERLY: 90,
    BillingInterval.HALF_YEARLY: 180,
    BillingInterval.YEARLY: 365,
}


class PlatformPlanListView(SuperAdminRequiredMixin, ListView):
    """List all SaaS subscription plans with status and pricing details."""
    template_name = "super_admin/plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return Plan.objects.all().order_by("display_order", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["billing_intervals"] = BillingInterval.choices
        ctx["total_active"] = Plan.objects.filter(is_active=True).count()
        ctx["total_public"] = Plan.objects.filter(is_active=True, is_public=True).count()
        return ctx


class PlatformPlanCreateEditView(SuperAdminRequiredMixin, View):
    """Create or Edit a SaaS Plan with all production fields."""
    template_name = "super_admin/plan_form.html"

    def _get_context(self, plan=None):
        return {
            "plan": plan,
            "billing_intervals": BillingInterval.choices,
            "duration_days_map": {k: v for k, v in DURATION_DAYS_MAP.items()},
        }

    def get(self, request, plan_id=None):
        plan = get_object_or_404(Plan, id=plan_id) if plan_id else None
        return render(request, self.template_name, self._get_context(plan))

    def post(self, request, plan_id=None):
        plan = get_object_or_404(Plan, id=plan_id) if plan_id else Plan()

        # ── Identity ──────────────────────────────────────────────────────────
        name = request.POST.get("name", "").strip()
        display_name = request.POST.get("display_name", "").strip()
        description = request.POST.get("description", "").strip()
        code = request.POST.get("code", "").strip()

        # ── Duration ──────────────────────────────────────────────────────────
        duration_type = request.POST.get("duration_type", BillingInterval.MONTHLY)
        custom_days = request.POST.get("custom_duration_days", "").strip()
        if duration_type == BillingInterval.CUSTOM and custom_days:
            duration_days = max(1, int(custom_days))
        else:
            duration_days = DURATION_DAYS_MAP.get(duration_type, 30)

        # ── Pricing ───────────────────────────────────────────────────────────
        def to_decimal(val, default="0.00"):
            try:
                return Decimal(val or default)
            except InvalidOperation:
                return Decimal(default)

        original_price = to_decimal(request.POST.get("original_price"))
        sale_price = to_decimal(request.POST.get("sale_price"))
        currency = request.POST.get("currency", "INR").strip().upper() or "INR"
        gst_inclusive = request.POST.get("gst_inclusive") == "on"
        gst_percentage = to_decimal(request.POST.get("gst_percentage", "18.00"), "18.00")

        # ── Trial ─────────────────────────────────────────────────────────────
        trial_eligible = request.POST.get("trial_eligible") == "on"
        trial_days = int(request.POST.get("trial_days") or 0)
        grace_days = int(request.POST.get("grace_days") or 7)

        # ── Display & Badges ──────────────────────────────────────────────────
        display_order = int(request.POST.get("display_order") or 0)
        is_active = request.POST.get("is_active") == "on"
        is_public = request.POST.get("is_public") == "on"
        is_featured = request.POST.get("is_featured") == "on"
        is_recommended = request.POST.get("is_recommended") == "on"
        is_popular = request.POST.get("is_popular") == "on"

        # Validation
        if not name:
            messages.error(request, "Plan Name is required.")
            return render(request, self.template_name, self._get_context(plan))

        with transaction.atomic():
            if not plan.id and not code:
                code = name.lower().replace(" ", "-")
            if not code:
                code = name.lower().replace(" ", "-")

            plan.code = code
            plan.name = name
            plan.display_name = display_name or name
            plan.description = description
            plan.duration_type = duration_type
            plan.duration_days = duration_days
            plan.original_price = original_price
            plan.sale_price = sale_price
            plan.currency = currency
            plan.gst_inclusive = gst_inclusive
            plan.gst_percentage = gst_percentage
            plan.trial_eligible = trial_eligible
            plan.trial_days = trial_days if trial_eligible else 0
            plan.grace_days = grace_days
            plan.display_order = display_order
            plan.is_active = is_active
            plan.is_public = is_public
            plan.is_featured = is_featured
            plan.is_recommended = is_recommended
            plan.is_popular = is_popular
            plan.features = {"all_pos_features": True}
            plan.save()

        action = "created" if not plan_id else "updated"
        messages.success(request, f"✓ Plan \"{plan.display_name or plan.name}\" {action} successfully!")
        return redirect("super_admin:plan_list")


class PlatformPlanDeleteView(SuperAdminRequiredMixin, View):
    """Delete a plan — protected if active subscribers exist."""

    def post(self, request, plan_id):
        plan = get_object_or_404(Plan, id=plan_id)

        # Check for active subscriptions on this plan
        try:
            from contexts.billing.models import Subscription
            active_count = Subscription.objects.filter(
                plan=plan,
                status__in=["trialing", "active", "past_due"],
            ).count()
            if active_count > 0:
                messages.error(
                    request,
                    f"Cannot delete \"{plan.name}\" — it has {active_count} active subscriber(s). "
                    "Deactivate it instead to hide it from new customers."
                )
                return redirect("super_admin:plan_list")
        except Exception:
            pass  # Subscription model may not exist yet — allow deletion

        plan_name = plan.name
        try:
            plan.delete()
            messages.success(request, f"Plan \"{plan_name}\" deleted successfully.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete \"{plan_name}\" because it is referenced by existing subscriptions (active or canceled). "
                "Please deactivate the plan instead to hide it from new customers."
            )
        return redirect("super_admin:plan_list")


class PlatformTrialConfigView(SuperAdminRequiredMixin, View):
    """Manage Global Free Trial settings across all plans/tenants."""
    template_name = "super_admin/trial_config.html"

    def get(self, request):
        config = GlobalTrialConfig.get_solo()
        return render(request, self.template_name, {"config": config})

    def post(self, request):
        config = GlobalTrialConfig.get_solo()
        config.is_enabled = request.POST.get("is_enabled") == "on"
        config.trial_days = int(request.POST.get("trial_days", "14"))
        config.grace_days = int(request.POST.get("grace_days", "7"))
        config.reminder_days_before = int(request.POST.get("reminder_days_before", "3"))
        config.require_card = request.POST.get("require_card") == "on"
        config.save()

        messages.success(request, "Global Free Trial configurations updated successfully!")
        return redirect("super_admin:trial_config")


class PlatformVisibilityConfigView(SuperAdminRequiredMixin, View):
    """Manage Duration / Interval visibility toggles across onboarding and upgrade flows."""
    template_name = "super_admin/visibility_config.html"

    def get(self, request):
        config = SubscriptionVisibilityConfig.get_solo()
        return render(request, self.template_name, {"config": config})

    def post(self, request):
        config = SubscriptionVisibilityConfig.get_solo()
        config.show_daily = request.POST.get("show_daily") == "on"
        config.show_weekly = request.POST.get("show_weekly") == "on"
        config.show_monthly = request.POST.get("show_monthly") == "on"
        config.show_quarterly = request.POST.get("show_quarterly") == "on"
        config.show_half_yearly = request.POST.get("show_half_yearly") == "on"
        config.show_yearly = request.POST.get("show_yearly") == "on"
        config.show_custom_duration = request.POST.get("show_custom_duration") == "on"
        config.show_currency = request.POST.get("show_currency") == "on"
        config.save()

        messages.success(request, "Subscription duration visibility toggles updated!")
        return redirect("super_admin:visibility_config")


class PlatformCouponDiscountListView(SuperAdminRequiredMixin, TemplateView):
    """List and manage SaaS Subscription Coupons & Discounts."""
    template_name = "super_admin/coupon_discount_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["coupons"] = SubscriptionCoupon.objects.all().order_by("-created_at")
        ctx["discounts"] = SubscriptionDiscount.objects.select_related("target_plan", "target_tenant").all().order_by("-created_at")
        return ctx


from django.utils.dateparse import parse_datetime

class PlatformCouponCreateEditView(SuperAdminRequiredMixin, View):
    """Create or Edit a SaaS promotional coupon."""
    template_name = "super_admin/coupon_form.html"

    def get(self, request, coupon_id=None):
        coupon = get_object_or_404(SubscriptionCoupon, id=coupon_id) if coupon_id else None
        plans = Plan.objects.filter(is_active=True)
        return render(request, self.template_name, {
            "coupon": coupon,
            "plans": plans,
        })

    def post(self, request, coupon_id=None):
        coupon = get_object_or_404(SubscriptionCoupon, id=coupon_id) if coupon_id else SubscriptionCoupon()
        
        # Identity
        coupon.name = request.POST.get("name", "").strip()
        coupon.code = request.POST.get("code", "").strip().upper()
        coupon.description = request.POST.get("description", "").strip()
        coupon.internal_notes = request.POST.get("internal_notes", "").strip()
        
        # Discount Rules
        coupon.discount_type = request.POST.get("discount_type", "percentage")
        
        def to_decimal(val, default="0.00"):
            try:
                return Decimal(val or default)
            except InvalidOperation:
                return Decimal(default)
                
        coupon.value = to_decimal(request.POST.get("value", "0"))
        coupon.minimum_purchase_amount = to_decimal(request.POST.get("minimum_purchase_amount")) if request.POST.get("minimum_purchase_amount") else None
        coupon.maximum_discount_amount = to_decimal(request.POST.get("maximum_discount_amount")) if request.POST.get("maximum_discount_amount") else None
        
        # Validity
        valid_from = parse_datetime(request.POST.get("valid_from")) if request.POST.get("valid_from") else timezone.now()
        coupon.valid_from = valid_from
        coupon.valid_until = parse_datetime(request.POST.get("valid_until")) if request.POST.get("valid_until") else None
        
        # Usage limits
        usage_limit = request.POST.get("usage_limit")
        coupon.usage_limit = int(usage_limit) if usage_limit else None
        coupon.per_user_limit = int(request.POST.get("per_user_limit", 1))
        
        # Status & Eligibility
        coupon.eligibility = request.POST.get("eligibility", "all")
        coupon.is_active = request.POST.get("is_active") == "on"
        coupon.is_hidden = request.POST.get("is_hidden") == "on"

        # Save and M2M
        with transaction.atomic():
            coupon.save()
            plan_ids = request.POST.getlist("applicable_plans")
            if plan_ids:
                coupon.applicable_plans.set(Plan.objects.filter(id__in=plan_ids))
            else:
                coupon.applicable_plans.clear()
                
        action = "created" if not coupon_id else "updated"
        messages.success(request, f"Coupon '{coupon.code}' {action} successfully!")
        return redirect("super_admin:coupon_discount_list")


class PlatformCouponDeleteView(SuperAdminRequiredMixin, View):
    """Delete a coupon (if not protected by existing usages)."""
    def post(self, request, coupon_id):
        coupon = get_object_or_404(SubscriptionCoupon, id=coupon_id)
        code = coupon.code
        try:
            coupon.delete()
            messages.success(request, f"Coupon '{code}' deleted.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{code}' as it has been used by subscribers. Deactivate it instead.")
        return redirect("super_admin:coupon_discount_list")


class PlatformCouponToggleStatusView(SuperAdminRequiredMixin, View):
    """Toggle a coupon's active status."""
    def post(self, request, coupon_id):
        coupon = get_object_or_404(SubscriptionCoupon, id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=["is_active"])
        status = "activated" if coupon.is_active else "deactivated"
        messages.success(request, f"Coupon '{coupon.code}' successfully {status}.")
        return redirect("super_admin:coupon_discount_list")


class PlatformTenantDiscountCreateView(SuperAdminRequiredMixin, View):
    """Create or edit a tenant-specific discount."""
    template_name = "super_admin/tenant_discount_form.html"

    def get(self, request, discount_id=None):
        discount = get_object_or_404(SubscriptionDiscount, id=discount_id) if discount_id else None
        from contexts.tenants.models import Tenant
        tenants = Tenant.objects.all().order_by("name")
        plans = Plan.objects.filter(is_active=True)
        return render(request, self.template_name, {
            "discount": discount,
            "tenants": tenants,
            "plans": plans,
        })

    def post(self, request, discount_id=None):
        discount = get_object_or_404(SubscriptionDiscount, id=discount_id) if discount_id else SubscriptionDiscount()
        from contexts.tenants.models import Tenant
        
        tenant_id = request.POST.get("target_tenant")
        plan_id = request.POST.get("target_plan")
        
        discount.target_tenant = get_object_or_404(Tenant, id=tenant_id) if tenant_id else None
        discount.target_plan = get_object_or_404(Plan, id=plan_id) if plan_id else None
        discount.discount_type = request.POST.get("discount_type", "percentage")
        
        def to_decimal(val, default="0.00"):
            try:
                return Decimal(val or default)
            except InvalidOperation:
                return Decimal(default)
                
        discount.value = to_decimal(request.POST.get("value", "0"))
        discount.scope = request.POST.get("scope", "forever")
        discount.duration_in_months = int(request.POST.get("duration_in_months") or 0) if discount.scope == 'repeating' else None
        discount.is_active = request.POST.get("is_active") == "on"
        
        discount.save()
        action = "created" if not discount_id else "updated"
        messages.success(request, f"Tenant discount override {action} successfully!")
        return redirect("super_admin:coupon_discount_list")

