"""Enterprise JWT Authentication Backend for DRF.

Extends DRF SimpleJWT authentication to enforce token_version validation
and account lockout / active status checks on every authenticated request.
"""
from typing import Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class EnterpriseJWTAuthentication(JWTAuthentication):
    """Extends DRF SimpleJWT authentication to verify token_version and lockout status."""

    def get_user(self, validated_token: Any) -> Any:
        user = super().get_user(validated_token)

        # Enforce instant global JWT revocation when token_version changes
        token_version = validated_token.get("token_version")
        if token_version is not None and token_version != user.token_version:
            raise AuthenticationFailed(
                "Session invalidated due to security reset or global logout."
            )

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        if user.is_currently_locked:
            raise AuthenticationFailed("User account is temporarily locked.")

        return user
