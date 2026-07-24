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
    SubscriptionInvoice,
)
from contexts.billing.gateways import get_gateway
from contexts.billing.services import invoice_service
from contexts.billing.services.license_service import LicenseService
from contexts.billing.services.pricing_engine import PricingEngine
from contexts.tenants.models import Tenant


class SubscriptionUpgradeView(LoginRequiredMixin, View):
    """View to display dynamic upgrade screen and handle renewals/upgrades."""
    template_name = "billing/upgrade.html"

    def _get_tenant(self, request):
        # Resolve tenant from context first (set by middleware)
        from shared.tenancy.context import get_current_tenant
        tenant_id = get_current_tenant()
        if tenant_id:
            try:
                return Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                pass
                
        tenant = getattr(request, "tenant", None)
        if not tenant:
            membership = getattr(request.user, "memberships", None)
            if membership and membership.exists():
                first_membership = membership.filter(tenant__isnull=False).first()
                if first_membership:
                    tenant = first_membership.tenant
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
                "effective_before_tax": pricing["effective_before_tax"],
                "gst_amount": pricing["gst_amount"],
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

        from shared.tenancy.context import tenant_context
        # Generate Razorpay Order and INCOMPLETE Subscription
        with tenant_context(tenant.id):
            session = LicenseService.create_checkout_session(
                tenant=tenant, new_plan=plan, interval=plan.duration_type, coupon_code=coupon_code
            )

        from django.conf import settings
        return JsonResponse({
            "status": "success",
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "order_id": session["order_id"],
            "amount_minor": session["amount_minor"],
            "currency": session["currency"],
            "invoice_number": session["invoice_number"],
            "plan_name": plan.name,
            "tenant_name": tenant.name,
        })

class VerifyPaymentAPIView(LoginRequiredMixin, View):
    """Synchronous payment verification for immediate dashboard redirection."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        payment_id = data.get("razorpay_payment_id")
        order_id = data.get("razorpay_order_id")
        signature = data.get("razorpay_signature")

        if not all([payment_id, order_id, signature]):
            return JsonResponse({"status": "error", "message": "Missing payment parameters."}, status=400)

        # 1. Verify signature
        gateway = get_gateway()
        if not gateway.verify_payment_signature(order_id, payment_id, signature):
            return JsonResponse({"status": "error", "message": "Invalid payment signature."}, status=400)

        # 2. Find the invoice and mark it paid (which also activates the subscription)
        from shared.tenancy import bypass_tenant
        with bypass_tenant():
            invoice = SubscriptionInvoice.all_objects.filter(provider_order_id=order_id).first()
        
        if not invoice:
            return JsonResponse({"status": "error", "message": "Invoice not found for this order."}, status=404)

        invoice_service.mark_paid(
            tenant_id=invoice.tenant_id,
            invoice=invoice,
            provider=gateway.name,
            provider_payment_id=payment_id,
        )

        return JsonResponse({
            "status": "success",
            "message": "Payment verified and subscription activated successfully!",
            "redirect_url": "/platform/tenant/dashboard/"
        })


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

class SubscriptionRestrictedView(LoginRequiredMixin, TemplateView):
    """View rendered when a user tries to access a protected feature without an active subscription."""
    template_name = "billing/restricted.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request, "tenant") and self.request.tenant:
            context["license_summary"] = LicenseService.get_license_summary(self.request.tenant)
        return context
