"""Clone system role templates into tenant-owned roles.

Called when a tenant is provisioned. Platform roles (Super Admin, Support) stay
global; COMPANY/BRANCH roles are copied so each tenant can customize its grants
without affecting others (true multi-tenant RBAC).
"""
import uuid

from django.db import transaction

from contexts.identity.models import Role, RolePermission


@transaction.atomic
def provision_tenant_roles(tenant_id: uuid.UUID) -> dict[str, Role]:
    """Copy non-platform system roles (and their grants) to a tenant.

    Idempotent: existing tenant roles with the same code are left untouched.
    Returns a mapping of role code -> tenant Role.
    """
    created: dict[str, Role] = {}
    system_roles = Role.objects.filter(
        tenant__isnull=True, is_system=True
    ).exclude(scope=Role.Scope.PLATFORM).prefetch_related("permissions")

    for template in system_roles:
        role, was_created = Role.objects.get_or_create(
            tenant_id=tenant_id,
            code=template.code,
            defaults={
                "name": template.name,
                "description": template.description,
                "scope": template.scope,
                "is_system": True,
            },
        )
        if was_created:
            RolePermission.objects.bulk_create(
                [
                    RolePermission(role=role, permission=perm)
                    for perm in template.permissions.all()
                ]
            )
        created[role.code] = role
    return created
