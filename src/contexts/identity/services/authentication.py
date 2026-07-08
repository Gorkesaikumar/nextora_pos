"""Enterprise authentication service.

Enforces brute-force lockout protection, multi-device session creation and revocation,
secure self-service password reset, and instant JWT version invalidation.
"""
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from contexts.identity.models.session import UserSession
from contexts.identity.models.tokens import PasswordResetToken, hash_token

User = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class EnterpriseAuthenticationService:
    @classmethod
    def authenticate_user(
        cls,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Any:
        """Authenticate user by email and password, enforcing account lockout policies."""
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid email or password.") from exc

        if not user.is_active:
            raise AuthenticationFailed("Account is disabled.")

        if user.is_currently_locked:
            raise AuthenticationFailed(
                "Account is temporarily locked due to repeated failed login attempts. "
                "Please try again later or request a password reset."
            )

        if not user.check_password(password):
            with transaction.atomic():
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = timezone.now() + timedelta(
                        minutes=LOCKOUT_DURATION_MINUTES
                    )
                user.save(update_fields=["failed_login_attempts", "locked_until"])
            raise AuthenticationFailed("Invalid email or password.")

        # Successful authentication: reset lockout metrics
        with transaction.atomic():
            user.failed_login_attempts = 0
            user.locked_until = None
            if ip_address:
                user.last_login_ip = ip_address
            user.save(update_fields=["failed_login_attempts", "locked_until", "last_login_ip"])

        return user

    @classmethod
    def create_user_session(
        cls,
        user: Any,
        token_jti: str,
        ip_address: str | None = None,
        user_agent: str = "",
        device_type: str = UserSession.DeviceType.DESKTOP,
    ) -> UserSession:
        """Record an active session for device tracking and revocation audit."""
        return UserSession.objects.create(
            user=user,
            token_jti=token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            last_active_at=timezone.now(),
            is_active=True,
        )

    @classmethod
    def revoke_session(cls, token_jti: str) -> bool:
        """Revoke a specific device session by token JTI."""
        session = UserSession.objects.filter(token_jti=token_jti, is_active=True).first()
        if session:
            session.revoke()
            return True
        return False

    @classmethod
    @transaction.atomic
    def revoke_all_user_sessions(cls, user: Any) -> int:
        """Revoke all active device sessions for a user and increment token_version.

        Incrementing token_version instantly invalidates all previously issued JWT access
        and refresh tokens system-wide.
        """
        user.token_version += 1
        user.save(update_fields=["token_version"])

        updated = UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False,
            revoked_at=timezone.now(),
        )
        return updated

    @classmethod
    @transaction.atomic
    def request_password_reset(cls, email: str) -> tuple[PasswordResetToken, str] | None:
        """Initiate secure password reset token generation."""
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            return None
        token_obj, raw_token = PasswordResetToken.create_for_user(user, expiry_minutes=60)
        return token_obj, raw_token

    @classmethod
    @transaction.atomic
    def confirm_password_reset(cls, raw_token: str, new_password: str) -> Any:
        """Validate SHA-256 token hash, update password, and revoke all active sessions."""
        hashed = hash_token(raw_token)
        token_obj = PasswordResetToken.objects.filter(
            token_hash=hashed,
            is_used=False,
        ).select_related("user").first()

        if not token_obj or not token_obj.is_valid:
            raise AuthenticationFailed("Password reset token is invalid or has expired.")

        user = token_obj.user
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.failed_login_attempts = 0
        user.locked_until = None
        user.token_version += 1
        user.save(
            update_fields=[
                "password",
                "password_changed_at",
                "failed_login_attempts",
                "locked_until",
                "token_version",
            ]
        )

        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False,
            revoked_at=timezone.now(),
        )
        return user
