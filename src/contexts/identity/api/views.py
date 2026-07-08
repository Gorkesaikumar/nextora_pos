"""Enterprise REST API views for authentication, session management, and credential security."""
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from contexts.identity.api.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserProfileSerializer,
    UserSessionSerializer,
)
from contexts.identity.models.session import UserSession
from contexts.identity.services.authentication import EnterpriseAuthenticationService
from shared.tenancy.context import get_current_tenant

User = get_user_model()


class CurrentUserView(views.APIView):
    """Retrieve authenticated user's profile and active tenancy context."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = UserProfileSerializer(request.user)
        data = serializer.data
        tenant = get_current_tenant()
        data["active_tenant"] = str(tenant) if tenant else None
        return Response(data, status=status.HTTP_200_OK)


class LogoutView(views.APIView):
    """Revoke specific refresh token session and blacklist token."""

    permission_classes = [IsAuthenticated]

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


class LogoutAllDevicesView(views.APIView):
    """Globally revoke all active device sessions and increment token_version."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        revoked_count = EnterpriseAuthenticationService.revoke_all_user_sessions(request.user)
        return Response(
            {"detail": "All active sessions revoked successfully.", "revoked_sessions": revoked_count},
            status=status.HTTP_200_OK,
        )


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """List and manage active device sessions for the authenticated user."""

    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke_device(self, request: Request, pk: str = None) -> Response:
        session = self.get_queryset().filter(pk=pk).first()
        if not session:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        session.revoke()
        return Response({"detail": "Device session revoked successfully."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(views.APIView):
    """Initiate password reset via secure SHA-256 hashed token."""

    permission_classes = [AllowAny]

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


class PasswordResetConfirmView(views.APIView):
    """Complete password reset and globally revoke all active sessions."""

    permission_classes = [AllowAny]

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
