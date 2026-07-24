import logging
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from contexts.billing.services.license_service import LicenseService

logger = logging.getLogger(__name__)

class SubscriptionAccessMiddleware:
    """
    Middleware that restricts access to premium features if the tenant's subscription is expired.
    Must run after TenantResolutionMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_prefixes = [
            "/auth/",
            "/billing/",
            "/styleguide/",
            "/healthz/",
            "/admin/",
            "/__debug__/",
            "/static/",
            "/media/",
        ]
        
    def __call__(self, request):
        from shared.tenancy.context import get_current_tenant
        
        tenant_id = get_current_tenant()
        if not tenant_id:
            return self.get_response(request)

        path = request.path_info

        # 2. Check if path is completely whitelisted
        if any(path.startswith(prefix) for prefix in self.allowed_prefixes):
            return self.get_response(request)

        # 3. Allow exact dashboard root
        if path == "/dashboard/":
            return self.get_response(request)

        # 4. Check license status
        # get_license_summary can accept a tenant object or an ID, but it's safer to pass the ID if it supports it, 
        # or we just pass the tenant_id and LicenseService will handle it (since it can take either).
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        
        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()
            
        summary = LicenseService.get_license_summary(tenant)
        if summary.get("is_expired", False) or not summary.get("can_transact", True):
            # Subscription is expired or restricted
            
            logger.warning(
                f"Access denied: User {getattr(request.user, 'email', 'Unknown')} attempted to access {path} with an expired subscription for tenant {tenant.name if tenant else 'Unknown'}."
            )
            
            if path.startswith("/api/"):
                return JsonResponse(
                    {
                        "status": "error",
                        "code": "subscription_expired",
                        "message": summary.get("banner_text", "Your subscription has expired. Please upgrade to continue."),
                    },
                    status=403
                )
            
            # Redirect to the restricted permission denied page
            return redirect("billing:restricted")

        return self.get_response(request)
