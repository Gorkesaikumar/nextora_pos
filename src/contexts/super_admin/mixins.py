from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """
    Ensure the user is a super admin (is_staff and is_superuser).
    Used exclusively for the Platform / Super Admin portal.
    """
    login_url = reverse_lazy('super_admin:login')

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_staff and user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(self.login_url)
        raise PermissionDenied("You do not have permission to access the Super Admin platform.")
