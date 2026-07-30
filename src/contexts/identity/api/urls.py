"""URL routing for enterprise REST API identity surface (/api/v1/auth/...)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contexts.identity.api.jwt import (
    EnterpriseTokenObtainPairView,
    EnterpriseTokenRefreshView,
)
from rest_framework_simplejwt.views import TokenVerifyView
from contexts.identity.api.views import (
    CurrentUserView,
    LogoutAllDevicesView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ChangePasswordView,
    UserSessionViewSet,
    UserMembershipViewSet,
    RoleViewSet,
    PermissionViewSet,
)

router = DefaultRouter()
router.register("sessions", UserSessionViewSet, basename="user-session")
router.register("memberships", UserMembershipViewSet, basename="user-membership")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")

urlpatterns = [
    path("token/", EnterpriseTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", EnterpriseTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllDevicesView.as_view(), name="logout_all_devices"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-change/", ChangePasswordView.as_view(), name="password_change"),
    path("", include(router.urls)),
]
