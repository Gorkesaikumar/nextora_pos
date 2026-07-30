"""Permission foundations for Nextora POS API."""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission as DRFBasePermission

from shared.tenancy.context import get_current_tenant


class BasePermission(DRFBasePermission):
    """Core permission validator for Nextora POS.

    Guarantees user is authenticated, active, and operating within a valid,
    resolved tenant scope (or has verified platform-level access).
    """

    def has_permission(self, request, view) -> bool:
        # Enforce authentication
        if not request.user or not request.user.is_authenticated:
            return False

        # Enforce active account status
        if not request.user.is_active:
            raise PermissionDenied("User account is disabled.")

        # Enforce lockout check
        if getattr(request.user, "is_currently_locked", False):
            raise PermissionDenied("User account is temporarily locked.")

        # Allow tenant-agnostic views to bypass resolved tenant validation
        if getattr(view, "tenant_agnostic", False):
            return True

        # Enforce resolved tenant isolation boundaries
        tenant_id = get_current_tenant()
        if tenant_id is None:
            # Let superuser pass
            if getattr(request.user, "is_superuser", False):
                return True

            # Platform staff support (tenant is null, but they have active membership)
            from contexts.identity.models import Membership
            from shared.tenancy.context import bypass_tenant

            with bypass_tenant():
                is_platform_staff = Membership.objects.filter(
                    user=request.user, tenant__isnull=True, is_active=True
                ).exists()

            if not is_platform_staff:
                raise PermissionDenied("Active tenant scope could not be resolved.")

        return True
