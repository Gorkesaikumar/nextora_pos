"""URL routing for enterprise REST API identity surface (/api/v1/auth/...)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contexts.identity.api.jwt import (
    EnterpriseTokenObtainPairView,
    EnterpriseTokenRefreshView,
)
from contexts.identity.api.views import (
    CurrentUserView,
    LogoutAllDevicesView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserSessionViewSet,
)

router = DefaultRouter()
router.register("sessions", UserSessionViewSet, basename="user-session")

urlpatterns = [
    path("token/", EnterpriseTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", EnterpriseTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllDevicesView.as_view(), name="logout_all_devices"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("", include(router.urls)),
]
