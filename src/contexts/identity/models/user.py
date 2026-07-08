"""Custom User model (email-identified, UUID PK).

See the project foundation notes: email is the login identifier, AUTH_USER_MODEL
is set before the first migration, and Django's auth machinery (password hashing,
PermissionsMixin) is reused rather than reinvented. RBAC authorization is layered
ON TOP via the Membership/Role/Permission tables and the authorization service —
it does not rely on Django's per-object permission framework.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from contexts.identity.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    full_name = models.CharField(_("full name"), max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # Django admin access only

    # Enterprise login security & token revocation fields
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    token_version = models.PositiveIntegerField(
        default=1,
        help_text="Incremented on logout-all or password change to instantly invalidate JWTs.",
    )
    is_email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "identity_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    @property
    def short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email

    @property
    def is_currently_locked(self) -> bool:
        """Return True if account is administratively locked or temporarily rate-locked."""
        if self.is_locked:
            return True
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False
