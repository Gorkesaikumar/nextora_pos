"""Enterprise JWT token issuance and refresh endpoints.

Provides TokenObtainPair serializers integrating EnterpriseAuthenticationService
to enforce brute-force defense and record multi-device UserSession ledgers.
"""
from typing import Any

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from contexts.identity.services.authentication import EnterpriseAuthenticationService
from shared.tenancy.context import get_current_tenant


class EnterpriseTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Issues JWT token pairs with enterprise security claims and session recording."""

    username_field = "email"

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs.get("email", "")
        password = attrs.get("password", "")

        request = self.context.get("request")
        ip_address = None
        user_agent = ""
        device_type = "desktop"
        if request:
            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            if "POS" in user_agent or request.headers.get("X-Device-Type") == "pos_terminal":
                device_type = "pos_terminal"
            elif "Mobile" in user_agent:
                device_type = "mobile"

        user = EnterpriseAuthenticationService.authenticate_user(
            email=email,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        refresh = RefreshToken.for_user(user)

        # Populate custom enterprise claims
        refresh["user_id"] = str(user.id)
        refresh["email"] = user.email
        refresh["token_version"] = user.token_version
        tenant = get_current_tenant()
        if tenant:
            refresh["tenant_id"] = str(tenant)

        # Record active session in UserSession ledger
        EnterpriseAuthenticationService.create_user_session(
            user=user,
            token_jti=str(refresh.payload.get("jti")),
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
        )

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": str(user.id),
            "token_version": user.token_version,
        }


class EnterpriseTokenObtainPairView(TokenObtainPairView):
    serializer_class = EnterpriseTokenObtainPairSerializer


class EnterpriseTokenRefreshView(TokenRefreshView):
    """Token refresh endpoint preserving token rotation and blacklisting."""
