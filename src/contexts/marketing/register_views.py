"""Onboarding wizard views.

Single-page wizard: GET renders the full form (Alpine.js drives step
visibility client-side). POST runs server-side validation on all 4 step forms
together; on success it provisions the workspace atomically, logs the operator
in, and redirects to the completion screen.
"""
from __future__ import annotations

from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, View

from contexts.billing.models import Plan
from contexts.marketing.forms import (
    AccountForm,
    BranchForm,
    PlanForm,
    RestaurantForm,
)
from contexts.marketing.services import ProvisioningError, provision_workspace


def _plans_context() -> list[dict]:
    """Active public plans + their cheapest INR monthly price, for the wizard
    plan cards."""
    plans = Plan.objects.filter(is_active=True, is_public=True)
    
    # Sort plans in the specific order requested by the client
    sort_order = {"starter": 1, "growth": 2, "professional": 3, "enterprise": 4}
    plans = sorted(plans, key=lambda p: sort_order.get(p.code, 99))
    out: list[dict] = []
    for plan in plans:
        prices = list(plan.prices.all())
        monthly = next((p for p in prices if p.interval == "monthly"), None)
        yearly = next((p for p in prices if p.interval == "yearly"), None)
        out.append({
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "trial_days": plan.trial_days,
            "max_branches": plan.max_branches,
            "max_employees": plan.max_employees,
            "monthly_amount": monthly.amount if (monthly and monthly.amount > 0) else None,
            "yearly_amount": yearly.amount if (yearly and yearly.amount > 0) else None,
            "currency": (monthly or yearly).currency if (monthly or yearly) else "INR",
            "features": plan.features or {},
        })
    return out


class RegisterView(View):
    template_name = "marketing/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("reporting:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self._render(request, forms={}, data={})

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
        return render(
            request,
            self.template_name,
            {
                "form_account": forms.get("account") or AccountForm(prefix="account"),
                "form_restaurant": forms.get("restaurant") or RestaurantForm(prefix="restaurant"),
                "form_plan": forms.get("plan") or PlanForm(prefix="plan"),
                "form_branch": forms.get("branch") or BranchForm(prefix="branch"),
                "plans": _plans_context(),
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
