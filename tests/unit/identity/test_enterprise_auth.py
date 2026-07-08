"""Enterprise Authentication & Authorization test suite."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from contexts.identity.models.session import UserSession
from contexts.identity.models.tokens import PasswordResetToken
from contexts.identity.services.authentication import EnterpriseAuthenticationService

User = get_user_model()


@pytest.mark.django_db
class TestEnterpriseAuthenticationService:
    def test_successful_authentication_resets_failures(self):
        user = User.objects.create_user(
            email="testauth@example.com",
            password="SecurePassword123!",
        )
        user.failed_login_attempts = 2
        user.save()

        auth_user = EnterpriseAuthenticationService.authenticate_user(
            "testauth@example.com",
            "SecurePassword123!",
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )
        assert auth_user.id == user.id
        auth_user.refresh_from_db()
        assert auth_user.failed_login_attempts == 0
        assert auth_user.locked_until is None
        assert auth_user.last_login_ip == "127.0.0.1"

    def test_brute_force_lockout_enforcement(self):
        user = User.objects.create_user(
            email="lockout@example.com",
            password="SecurePassword123!",
        )
        for _ in range(5):
            with pytest.raises(AuthenticationFailed):
                EnterpriseAuthenticationService.authenticate_user(
                    "lockout@example.com", "WrongPassword!"
                )

        user.refresh_from_db()
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.is_currently_locked is True

        # Even with correct password, locked account must fail
        with pytest.raises(AuthenticationFailed) as exc_info:
            EnterpriseAuthenticationService.authenticate_user(
                "lockout@example.com", "SecurePassword123!"
            )
        assert "temporarily locked" in str(exc_info.value)

    def test_create_and_revoke_user_sessions(self):
        user = User.objects.create_user(
            email="sessions@example.com",
            password="SecurePassword123!",
        )
        s1 = EnterpriseAuthenticationService.create_user_session(
            user=user,
            token_jti="jti-desktop",
            device_type="desktop",
        )
        s2 = EnterpriseAuthenticationService.create_user_session(
            user=user,
            token_jti="jti-pos",
            device_type="pos_terminal",
        )
        assert UserSession.objects.filter(user=user, is_active=True).count() == 2

        revoked = EnterpriseAuthenticationService.revoke_session("jti-pos")
        assert revoked is True
        assert UserSession.objects.filter(user=user, is_active=True).count() == 1

        # Global revocation
        revoked_all = EnterpriseAuthenticationService.revoke_all_user_sessions(user)
        assert revoked_all == 1
        assert UserSession.objects.filter(user=user, is_active=True).count() == 0
        user.refresh_from_db()
        assert user.token_version == 2

    def test_password_reset_revokes_all_sessions_and_tokens(self):
        user = User.objects.create_user(
            email="reset@example.com",
            password="OldPassword123!",
        )
        EnterpriseAuthenticationService.create_user_session(
            user=user, token_jti="jti-before-reset"
        )
        token_obj, raw_token = EnterpriseAuthenticationService.request_password_reset(
            "reset@example.com"
        )
        assert token_obj is not None

        updated_user = EnterpriseAuthenticationService.confirm_password_reset(
            raw_token, "NewSecurePassword456!"
        )
        updated_user.refresh_from_db()
        assert updated_user.check_password("NewSecurePassword456!") is True
        assert updated_user.password_changed_at is not None
        assert updated_user.token_version == 2
        assert UserSession.objects.filter(user=user, is_active=True).count() == 0
