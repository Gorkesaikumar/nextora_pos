"""Onboarding wizard views.

Single-page wizard: GET renders the full form (Alpine.js drives step
visibility client-side). POST runs server-side validation on all 4 step forms
together; on success it provisions the workspace atomically, logs the operator
in, and redirects to the completion screen.
"""
from __future__ import annotations

from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, View
from decimal import Decimal

from contexts.billing.models import Plan, SubscriptionVisibilityConfig, SubscriptionCoupon
from contexts.billing.domain.enums import BillingInterval
from contexts.marketing.forms import (
    AccountForm,
    BranchForm,
    PlanForm,
    RestaurantForm,
)
from contexts.marketing.services import ProvisioningError, provision_workspace


def _plans_context() -> list[dict]:
    """Active public plans, using exact Plan duration and pricing."""
    plans = Plan.objects.filter(is_active=True, is_public=True).order_by("display_order", "name")
    
    out: list[dict] = []
    for plan in plans:
        out.append({
            "id": str(plan.id),
            "code": plan.code,
            "name": plan.display_name or plan.name,
            "description": plan.description or "100% Nextora POS Features Included",
            "trial_days": plan.trial_days,
            "duration_type": plan.duration_type,
            "duration_days": plan.duration_days,
            "duration_display": plan.get_duration_type_display(),
            "original_price": plan.original_price,
            "sale_price": plan.sale_price,
            "effective_price": plan.effective_price,
            "has_discount": plan.has_discount,
            "currency": plan.currency or "INR",
            "is_featured": plan.is_featured,
            "is_recommended": plan.is_recommended,
            "is_popular": plan.is_popular,
            "is_default": plan.is_default,
        })
    return out


class RegisterView(View):
    template_name = "marketing/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("reporting:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        forms = {}
        plan_code = request.GET.get('plan')
        if plan_code:
            forms['plan'] = PlanForm(initial={'plan_code': plan_code}, prefix="plan")
        return self._render(request, forms=forms, data={})

    def post(self, request, *args, **kwargs):
        data = request.POST
        account = AccountForm(data, prefix="account")
        restaurant = RestaurantForm(data, prefix="restaurant")
        plan = PlanForm(data, prefix="plan")
        branch = BranchForm(data, prefix="branch")

        all_valid = all([account.is_valid(), restaurant.is_valid(),
                         plan.is_valid(), branch.is_valid()])

        if not all_valid:
            return self._render(
                request,
                forms={"account": account, "restaurant": restaurant,
                       "plan": plan, "branch": branch},
                data=data,
                status=422,
            )

        try:
            workspace = provision_workspace(
                account=account.cleaned_data,
                restaurant=restaurant.cleaned_data,
                plan=plan.cleaned_data,
                branch=branch.cleaned_data,
            )
        except ProvisioningError as exc:
            account.add_error(None, str(exc))
            return self._render(
                request,
                forms={"account": account, "restaurant": restaurant,
                       "plan": plan, "branch": branch},
                data=data,
                status=422,
            )

        login(
            request,
            workspace.user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        # Instead of redirecting to register_complete, return success state to show Celebration Modal
        return self._render(
            request,
            forms={"account": account, "restaurant": restaurant,
                   "plan": plan, "branch": branch},
            data=data,
            status=200,
            success=True,
            workspace=workspace,
        )

    def _render(self, request, *, forms: dict, data, status: int = 200, success: bool = False, workspace = None):
        from contexts.billing.models import GlobalTrialConfig
        return render(
            request,
            self.template_name,
            {
                "form_account": forms.get("account") or AccountForm(prefix="account"),
                "form_restaurant": forms.get("restaurant") or RestaurantForm(prefix="restaurant"),
                "form_plan": forms.get("plan") or PlanForm(prefix="plan"),
                "form_branch": forms.get("branch") or BranchForm(prefix="branch"),
                "plans": _plans_context(),
                "visible_intervals": SubscriptionVisibilityConfig.get_solo().get_visible_intervals(),
                "trial_config": GlobalTrialConfig.get_solo(),
                "submitted": bool(forms),
                "success": success,
                "workspace": workspace,
            },
            status=status,
        )



class RegisterCompleteView(TemplateView):
    template_name = "marketing/register_complete.html"

    def dispatch(self, request, *args, **kwargs):
        # Anonymous users have no workspace to celebrate.
        if not request.user.is_authenticated:
            return redirect("marketing:register")
        return super().dispatch(request, *args, **kwargs)


class ValidateCouponAPIView(View):
    """AJAX endpoint to validate a coupon code during registration."""
    def post(self, request):
        code = request.POST.get("coupon_code", "").strip().upper()
        plan_code = request.POST.get("plan_code")
        
        if not code:
            return JsonResponse({"valid": False, "error": "No coupon code provided."})
            
        try:
            coupon = SubscriptionCoupon.objects.get(code=code)
        except SubscriptionCoupon.DoesNotExist:
            return JsonResponse({"valid": False, "error": "Invalid coupon code."})
            
        # Is it active?
        is_valid, msg = coupon.is_valid_now(tenant_status="new")
        if not is_valid:
            return JsonResponse({"valid": False, "error": msg})
            
        # Does it apply to the selected plan?
        if plan_code:
            try:
                plan = Plan.objects.get(code=plan_code)
                if coupon.applicable_plans.exists() and not coupon.applicable_plans.filter(id=plan.id).exists():
                    return JsonResponse({"valid": False, "error": "This coupon cannot be applied to the selected plan."})
                    
                # Check minimum purchase against plan effective price
                if coupon.minimum_purchase_amount and plan.effective_price < coupon.minimum_purchase_amount:
                    return JsonResponse({"valid": False, "error": f"Minimum purchase of ₹{coupon.minimum_purchase_amount} required."})
            except Plan.DoesNotExist:
                pass
                
        # Prepare response
        data = {
            "valid": True,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "value": str(coupon.value),
        }
        if coupon.maximum_discount_amount:
            data["maximum_discount_amount"] = str(coupon.maximum_discount_amount)
            
        return JsonResponse(data)
