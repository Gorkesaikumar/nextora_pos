from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.template.response import TemplateResponse
from django.views.generic import RedirectView

from contexts.identity.forms import CustomAuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from contexts.billing.services.license_service import LicenseService


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Superusers skip tenant selection and go straight to the dashboard.
        if self.request.user.is_superuser:
            return reverse_lazy("reporting:home")
        # Redirect to the tenant selection screen after login
        return reverse_lazy("tenants:select_tenant")

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.headers.get('HX-Request'):
            # If HTMX, return the form with errors inside the HTMX target
            return TemplateResponse(
                self.request,
                self.template_name,
                {"form": form},
                status=422
            )
        return response


class IdentityLogoutView(LogoutView):
    next_page = reverse_lazy("identity:login")

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        from django.contrib import messages
        messages.success(request, "You have been logged out successfully.")
        return response

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "identity/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from shared.tenancy.context import get_current_tenant
        from contexts.tenants.models import Tenant
        tenant_id = get_current_tenant() or getattr(self.request, "tenant_id", None)
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                context["license_summary"] = LicenseService.get_license_summary(tenant)
            except Tenant.DoesNotExist:
                pass
        return context
