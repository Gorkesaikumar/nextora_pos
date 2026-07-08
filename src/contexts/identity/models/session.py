"""Enterprise multi-device session tracking ledger.

Every login across web browser, POS touch terminal, or mobile client creates a UserSession row.
Allows users and security administrators to inspect active sessions, revoke individual devices,
or terminate all active sessions globally.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class UserSession(UUIDModel, TimeStampedModel):
    __rls_exempt__ = True

    class DeviceType(models.TextChoices):
        DESKTOP = "desktop", "Desktop"
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"
        POS_TERMINAL = "pos_terminal", "POS Touch Terminal"
        API = "api", "API Client"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    token_jti = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="JWT refresh token JTI or Django session key.",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(
        max_length=32,
        choices=DeviceType.choices,
        default=DeviceType.DESKTOP,
    )
    browser = models.CharField(max_length=64, blank=True)
    operating_system = models.CharField(max_length=64, blank=True)

    last_active_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "identity_user_session"
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="ix_user_session__user_active",
            ),
        ]

    def __str__(self) -> str:
        return f"Session {self.id} for {self.user_id} ({self.device_type})"

    def touch(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = timezone.now()
        self.save(update_fields=["last_active_at"])

    def revoke(self) -> None:
        """Revoke this specific session."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])
