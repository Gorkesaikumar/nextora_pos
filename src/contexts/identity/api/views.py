"""Enterprise REST API views for authentication, session management, and credential security."""
from typing import Any

from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view

from django.contrib.auth import get_user_model
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from contexts.identity.api.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ChangePasswordSerializer,
    UserProfileSerializer,
    UserSessionSerializer,
    RoleSerializer,
    PermissionSerializer,
)
from contexts.identity.models.session import UserSession
from contexts.identity.services.authentication import EnterpriseAuthenticationService
from shared.tenancy.context import get_current_tenant
from shared.api.views import BaseAPIView, BaseModelViewSet

User = get_user_model()


class CurrentUserView(BaseAPIView):
    """Retrieve or update authenticated user's profile and active tenancy context."""

    tenant_agnostic = True

    @extend_schema(responses={200: UserProfileSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = UserProfileSerializer(request.user)
        data = serializer.data
        tenant_id = get_current_tenant()
        if not tenant_id:
            from contexts.identity.models import Membership
            from shared.tenancy.context import bypass_tenant
            with bypass_tenant():
                m = Membership.objects.filter(user=request.user, is_active=True, tenant__isnull=False).first()
                if m:
                    tenant_id = m.tenant_id

        if tenant_id:
            from contexts.tenants.models import Tenant
            from shared.tenancy.context import bypass_tenant
            with bypass_tenant():
                t = Tenant.objects.filter(id=tenant_id).first()
                data["active_tenant"] = t.name if t else str(tenant_id)
                data["tenant_id"] = str(tenant_id)
        else:
            data["active_tenant"] = None
            data["tenant_id"] = None
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(request=UserProfileSerializer, responses={200: UserProfileSerializer})
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = serializer.data
        tenant_id = get_current_tenant()
        if tenant_id:
            from contexts.tenants.models import Tenant
            from shared.tenancy.context import bypass_tenant
            with bypass_tenant():
                t = Tenant.objects.filter(id=tenant_id).first()
                data["active_tenant"] = t.name if t else str(tenant_id)
                data["tenant_id"] = str(tenant_id)
        else:
            data["active_tenant"] = None
            data["tenant_id"] = None
        return Response(data, status=status.HTTP_200_OK)


class LogoutView(BaseAPIView):
    """Revoke specific refresh token session and blacklist token."""

    tenant_agnostic = True

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()
                jti = token.payload.get("jti")
                if jti:
                    EnterpriseAuthenticationService.revoke_session(str(jti))
            except Exception:
                pass
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class LogoutAllDevicesView(BaseAPIView):
    """Globally revoke all active device sessions and increment token_version."""

    tenant_agnostic = True

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        revoked_count = EnterpriseAuthenticationService.revoke_all_user_sessions(request.user)
        return Response(
            {"detail": "All active sessions revoked successfully.", "revoked_sessions": revoked_count},
            status=status.HTTP_200_OK,
        )


class UserSessionViewSet(BaseModelViewSet):
    """List and manage active device sessions for the authenticated user."""

    serializer_class = UserSessionSerializer
    tenant_agnostic = True
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke_device(self, request: Request, pk: str = None) -> Response:
        session = self.get_queryset().filter(pk=pk).first()
        if not session:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        session.revoke()
        return Response({"detail": "Device session revoked successfully."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(BaseAPIView):
    """Initiate password reset via secure SHA-256 hashed token."""

    permission_classes = [AllowAny]
    tenant_agnostic = True

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = EnterpriseAuthenticationService.request_password_reset(
            email=serializer.validated_data["email"]
        )
        # Always return success to prevent email enumeration
        return Response(
            {"detail": "If an active account exists, password reset instructions have been issued."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(BaseAPIView):
    """Complete password reset and globally revoke all active sessions."""

    permission_classes = [AllowAny]
    tenant_agnostic = True

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        EnterpriseAuthenticationService.confirm_password_reset(
            raw_token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response(
            {"detail": "Password reset successfully. All existing sessions have been terminated."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(BaseAPIView):
    """Change the authenticated user's password."""
    tenant_agnostic = True

    @extend_schema(request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data.get("old_password")):
            return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data.get("new_password"))
        user.save()
        
        # Revoke all sessions so the user has to login again
        EnterpriseAuthenticationService.revoke_all_user_sessions(user)

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)


from shared.api.views import BaseModelViewSet
from contexts.identity.models import Membership, Role, Permission
from contexts.identity.api.serializers import UserMembershipSerializer
from shared.tenancy.context import bypass_tenant


class UserMembershipViewSet(BaseModelViewSet):
    """ViewSet to list active memberships for the authenticated user."""

    serializer_class = UserMembershipSerializer
    tenant_agnostic = True  # Allows list retrieval before active tenant is selected

    def get_queryset(self):
        with bypass_tenant():
            return (
                Membership.objects.filter(
                    user=self.request.user,
                    is_active=True,
                )
                .select_related("tenant", "role")
                .all()
            )


@extend_schema_view(
    list=extend_schema(description="List available roles for the current context"),
    retrieve=extend_schema(description="Retrieve role details"),
)
class RoleViewSet(BaseModelViewSet):
    """Read-only ViewSet to list available roles."""
    serializer_class = RoleSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        tenant_id = get_current_tenant()
        # Roles accessible are either global system roles, or roles specific to the tenant
        return Role.objects.filter(
            Q(tenant_id=tenant_id) | Q(tenant__isnull=True)
        ).prefetch_related("permissions")


@extend_schema_view(
    list=extend_schema(description="List all available system permissions"),
    retrieve=extend_schema(description="Retrieve permission details"),
)
class PermissionViewSet(BaseModelViewSet):
    """Read-only ViewSet to list system permissions."""
    serializer_class = PermissionSerializer
    http_method_names = ["get"]
    tenant_agnostic = True
    
    def get_queryset(self):
        return Permission.objects.all()
