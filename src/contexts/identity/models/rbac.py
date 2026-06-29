"""RBAC tables: Permission, Role, RolePermission, Membership.

Everything about *who can do what* is data here — there are no role->permission
mappings in code. The catalog of permission CODES is declared per-context and
synced into the ``permission`` table; grants and memberships are fully editable
rows.

These tables carry a nullable ``tenant_id`` (NULL = platform/system scope), so
they are marked ``__rls_exempt__`` — the RLS predicate ``tenant_id = current``
would otherwise hide platform rows. Tenant scoping for them is enforced in the
authorization service queries instead.
"""
import uuid

from django.conf import settings
from django.db import models

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class Permission(UUIDModel, TimeStampedModel):
    """Global catalog of capabilities. Synced from each context's declaration."""

    code = models.CharField(max_length=100, unique=True)   # "orders.void"
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, db_index=True)  # "ordering"

    class Meta:
        db_table = "permission"
        ordering = ["module", "code"]

    def __str__(self) -> str:
        return self.code


class Role(UUIDModel, TimeStampedModel):
    __rls_exempt__ = True

    class Scope(models.TextChoices):
        PLATFORM = "platform"   # crosses tenants (Super Admin, Support)
        COMPANY = "company"     # all branches of one tenant
        BRANCH = "branch"       # one branch only

    # NULL tenant = system/platform role (a shared template or platform role).
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=50)          # "cashier"
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    scope = models.CharField(
        max_length=16, choices=Scope.choices, default=Scope.COMPANY
    )
    is_system = models.BooleanField(default=False)  # seeded; protected from edits

    permissions = models.ManyToManyField(
        Permission, through="RolePermission", related_name="roles"
    )

    class Meta:
        db_table = "role"
        constraints = [
            # Role code unique within a tenant.
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uq_role__tenant_code"
            ),
            # Among system/platform roles (tenant NULL), code is globally unique
            # (NULLs are distinct in SQL, so a partial unique index is needed).
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(tenant__isnull=True),
                name="uq_role__system_code",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"], name="ix_role__tenant"),
        ]

    def __str__(self) -> str:
        return f"{self.code}{'' if self.tenant_id else ' (system)'}"


class RolePermission(UUIDModel):
    """The editable grant table — the heart of 'database-driven permissions'."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="grants")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="grants"
    )

    class Meta:
        db_table = "role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="uq_role_permission"
            ),
        ]
        indexes = [
            models.Index(fields=["permission"], name="ix_role_perm__permission"),
        ]


class Membership(UUIDModel, TimeStampedModel):
    """Binds a user to a role within a tenant (and optionally a branch)."""

    __rls_exempt__ = True

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    # NULL tenant = platform membership (Super Admin / Support).
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="memberships",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    # NULL = all branches (company/platform scope). Set = branch-scoped.
    # Soft reference to tenants.Location (added with the inventory/branch work).
    location_id = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "membership"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant", "role", "location_id"],
                name="uq_membership__user_tenant_role_location",
            ),
        ]
        indexes = [
            # The resolver's primary query: a user's active memberships.
            models.Index(
                fields=["user", "tenant"],
                name="ix_membership__user_tenant",
                condition=models.Q(is_active=True),
            ),
            models.Index(fields=["role"], name="ix_membership__role"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.role_id}"
