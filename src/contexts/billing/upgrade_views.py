"""Subscription Upgrade & Renewal Views for Tenant Operators."""
from __future__ import annotations

import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from contexts.billing.models import (
    Plan,
    Subscription,
    SubscriptionVisibilityConfig,
    GlobalTrialConfig,
)
from contexts.billing.services.license_service import LicenseService
from contexts.billing.services.pricing_engine import PricingEngine
from contexts.tenants.models import Tenant


class SubscriptionUpgradeView(LoginRequiredMixin, View):
    """View to display dynamic upgrade screen and handle renewals/upgrades."""
    template_name = "billing/upgrade.html"

    def _get_tenant(self, request):
        # Resolve tenant from request context or user membership
        tenant = getattr(request, "tenant", None)
        if not tenant:
            membership = getattr(request.user, "memberships", None)
            if membership and membership.exists():
                tenant = membership.first().tenant
        return tenant

    def get(self, request, *args, **kwargs):
        tenant = self._get_tenant(request)
        if not tenant:
            return redirect("marketing:register")

        summary = LicenseService.get_license_summary(tenant)
        plans = Plan.objects.filter(is_active=True, is_public=True).order_by("display_order", "name")
        visibility = SubscriptionVisibilityConfig.get_solo()
        trial_config = GlobalTrialConfig.get_solo()

        plan_cards = []
        for plan in plans:
            # Calculate price for current tenant (with override if any)
            pricing = PricingEngine.calculate_effective_price(tenant, plan)

            plan_cards.append({
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.display_name or plan.name,
                "description": plan.description or "100% Nextora POS Features Included",
                "duration_days": plan.duration_days,
                "duration_display": plan.get_duration_type_display(),
                "total_amount": pricing["total_amount"],
                "currency": plan.currency or "INR",
                "is_featured": plan.is_featured,
                "is_recommended": plan.is_recommended,
                "is_popular": plan.is_popular,
                "is_current": summary.get("plan_code") == plan.code,
            })

        return render(
            request,
            self.template_name,
            {
                "summary": summary,
                "plans": plan_cards,
                "trial_config": trial_config,
                "tenant": tenant,
            },
        )

    def post(self, request, *args, **kwargs):
        """Handle upgrade/renewal form submission via JSON or form POST."""
        tenant = self._get_tenant(request)
        if not tenant:
            return JsonResponse({"status": "error", "message": "Tenant not found"}, status=400)

        plan_code = request.POST.get("plan_code")
        coupon_code = request.POST.get("coupon_code", "").strip()

        plan = get_object_or_404(Plan, code=plan_code, is_active=True)

        # Validate pricing and coupon first
        pricing = PricingEngine.calculate_effective_price(
            tenant=tenant, plan=plan, coupon_code=coupon_code
        )

        if coupon_code and not pricing["coupon_valid"]:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accepts("application/json"):
                return JsonResponse({"status": "error", "message": pricing["coupon_error"]}, status=400)

        # Execute renewal / upgrade
        # Note: LicenseService.renew_or_upgrade may need interval removed if it relies on it. 
        # But we pass plan's duration_type
        sub = LicenseService.renew_or_upgrade(
            tenant=tenant, new_plan=plan, interval=plan.duration_type, coupon_code=coupon_code
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accepts("application/json"):
            return JsonResponse({
                "status": "success",
                "message": f"Successfully upgraded/renewed to {plan.name}!",
                "redirect_url": "/billing/dashboard/",
            })

        return redirect("billing:dashboard")


class ValidateCouponAPIView(LoginRequiredMixin, View):
    """API endpoint to validate coupon instantly on the upgrade screen."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        plan_code = data.get("plan_code")
        coupon_code = data.get("coupon_code", "").strip()

        plan = Plan.objects.filter(code=plan_code, is_active=True).first()
        if not plan:
            return JsonResponse({"status": "error", "message": "Plan not found."}, status=404)

        # Resolve tenant
        tenant = getattr(request, "tenant", None)
        if not tenant:
            membership = getattr(request.user, "memberships", None)
            if membership and membership.exists():
                tenant = membership.first().tenant

        pricing = PricingEngine.calculate_effective_price(
            tenant=tenant, plan=plan, coupon_code=coupon_code
        )

        if coupon_code and not pricing["coupon_valid"]:
            return JsonResponse({
                "status": "error",
                "message": pricing["coupon_error"],
            }, status=400)

        return JsonResponse({
            "status": "success",
            "message": "Coupon applied successfully!",
            "base_price": float(pricing["base_price"]),
            "discount_amount": float(pricing["discount_amount"] + pricing["coupon_discount"]),
            "gst_amount": float(pricing["gst_amount"]),
            "total_amount": float(pricing["total_amount"]),
            "currency": pricing["currency"],
        })
