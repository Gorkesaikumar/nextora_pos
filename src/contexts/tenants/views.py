from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from contexts.identity.models import Membership
from contexts.tenants.models import Tenant
from shared.tenancy.context import bypass_tenant


def _active_memberships(user):
    """The user's active memberships to a real, usable tenant.

    A user's tenant access lives in ``identity.Membership`` — NOT in
    ``employees.EmployeeProfile`` (a separate HR record that most owners never
    have). Querying the wrong table is what locked legitimate owners out of the
    workspace picker.

    Runs under ``bypass_tenant`` because no tenant is bound during selection,
    so the tenant-scoped managers would otherwise fail closed to an empty set.
    """
    with bypass_tenant():
        memberships = list(
            Membership.objects.filter(
                user=user, is_active=True, tenant__isnull=False
            )
            .select_related("tenant", "role")
            .order_by("tenant__name")
        )
    # Hide suspended/churned tenants — only TRIAL/ACTIVE are usable.
    return [m for m in memberships if m.tenant.is_active]


def _activate(request, tenant):
    """Persist the chosen workspace and land on the dashboard.

    The tenant middleware reads ``active_tenant_id`` from the session to scope
    the request to this workspace.
    """
    request.session["active_tenant_id"] = str(tenant.id)
    return redirect(reverse("reporting:home"))


class TenantSelectView(LoginRequiredMixin, TemplateView):
    template_name = "tenants/select_tenant.html"

    def get(self, request, *args, **kwargs):
        memberships = _active_memberships(request.user)
        # A single workspace needs no choice — skip the picker entirely.
        if len(memberships) == 1:
            return _activate(request, memberships[0].tenant)
        self._memberships = memberships
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["memberships"] = getattr(self, "_memberships", [])
        return context


class SetTenantView(LoginRequiredMixin, View):
    def get(self, request, slug, *args, **kwargs):
        with bypass_tenant():
            tenant = get_object_or_404(Tenant, slug=slug)
            # Verify membership server-side; never trust the slug alone.
            has_access = Membership.objects.filter(
                user=request.user, tenant=tenant, is_active=True
            ).exists()

        if has_access and tenant.is_active:
            return _activate(request, tenant)

        return redirect("tenants:select_tenant")
