"""Create/refresh the system role templates and their default grants.

Idempotent. Syncs permissions first, then for each blueprint upserts a system
role (tenant = NULL, is_system = True) and reconciles its grants to match the
blueprint. These are DEFAULTS — once seeded, admins may edit grants in the DB,
and per-tenant copies are made by provision_tenant_roles().
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from contexts.identity.models import Permission, Role, RolePermission
from contexts.identity.permissions import ROLE_BLUEPRINTS, resolve_blueprint_codes


class Command(BaseCommand):
    help = "Seed the nine enterprise system roles with default permissions."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        call_command("sync_permissions")
        perms_by_code = {p.code: p for p in Permission.objects.all()}

        for bp in ROLE_BLUEPRINTS:
            role, _ = Role.objects.update_or_create(
                tenant=None,
                code=bp.code,
                defaults={
                    "name": bp.name,
                    "scope": bp.scope,
                    "is_system": True,
                },
            )
            desired = resolve_blueprint_codes(bp)
            existing = set(
                role.permissions.values_list("code", flat=True)
            )

            # Add missing grants.
            to_add = desired - existing
            RolePermission.objects.bulk_create(
                [
                    RolePermission(role=role, permission=perms_by_code[code])
                    for code in to_add
                    if code in perms_by_code
                ]
            )
            # Remove grants no longer in the blueprint.
            to_remove = existing - desired
            if to_remove:
                RolePermission.objects.filter(
                    role=role, permission__code__in=to_remove
                ).delete()

            self.stdout.write(
                f"  {bp.code}: {len(desired)} permissions "
                f"(+{len(to_add)} / -{len(to_remove)})"
            )

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(ROLE_BLUEPRINTS)} system roles.")
        )
