"""Secure cryptographic tokens for self-service password reset and email verification.

Stores SHA-256 hashes of generated one-time tokens with strict expiration thresholds.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


def hash_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PasswordResetToken(UUIDModel, TimeStampedModel):
    __rls_exempt__ = True

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "identity_password_reset_token"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user: models.Model, expiry_minutes: int = 60) -> tuple["PasswordResetToken", str]:
        """Generate a cryptographically random token string and save its SHA-256 hash."""
        raw_token = secrets.token_urlsafe(32)
        hashed = hash_token(raw_token)
        token_obj = cls.objects.create(
            user=user,
            token_hash=hashed,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )
        return token_obj, raw_token

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() <= self.expires_at


class EmailVerificationToken(UUIDModel, TimeStampedModel):
    __rls_exempt__ = True

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "identity_email_verification_token"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user: models.Model, expiry_hours: int = 24) -> tuple["EmailVerificationToken", str]:
        """Generate a cryptographically random token string and save its SHA-256 hash."""
        raw_token = secrets.token_urlsafe(32)
        hashed = hash_token(raw_token)
        token_obj = cls.objects.create(
            user=user,
            token_hash=hashed,
            expires_at=timezone.now() + timedelta(hours=expiry_hours),
        )
        return token_obj, raw_token

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() <= self.expires_at
