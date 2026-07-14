from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.contrib.auth.mixins import AccessMixin

from contexts.identity.services.authorization import has_permission

class TenantPermissionRequiredMixin(AccessMixin):
    """Verify that the current user has a specific permission in the current tenant."""
    
    permission_required = None

    def get_permission_required(self):
        """
        Override this method to override the permission_required attribute.
        Must return an iterable.
        """
        if self.permission_required is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} is missing the "
                f"permission_required attribute. Define "
                f"{self.__class__.__name__}.permission_required, or override "
                f"{self.__class__.__name__}.get_permission_required()."
            )
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required

    def has_permission(self):
        """
        Override this method to customize the way permissions are checked.
        """
        perms = self.get_permission_required()
        
        # We need the tenant_id. Since our app is tenant-aware, it should be on request.
        tenant_id = getattr(self.request, 'tenant_id', None)
            
        # We also might have a branch_id (location_id) on the request.
        location_id = getattr(self.request, 'branch_id', None)

        for perm in perms:
            if not has_permission(self.request.user, perm, tenant_id):
                return False
        return True

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
