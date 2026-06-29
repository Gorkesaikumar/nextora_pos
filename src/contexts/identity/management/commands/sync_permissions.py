"""Upsert the declared permission catalog into the database.

Run after deploys. Each bounded context declares its capability codes in
permissions/catalog.py; this command makes the DB match. Stale permissions
(no longer declared) are reported but NOT deleted automatically (deleting a
permission would silently revoke grants — that must be a deliberate migration).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from contexts.identity.models import Permission
from contexts.identity.permissions import PERMISSIONS


class Command(BaseCommand):
    help = "Synchronise the permission catalog from code into the database."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created = updated = 0
        declared = {p.code for p in PERMISSIONS}

        for pdef in PERMISSIONS:
            obj, was_created = Permission.objects.update_or_create(
                code=pdef.code,
                defaults={"name": pdef.name, "module": pdef.module},
            )
            created += int(was_created)
            updated += int(not was_created)

        stale = (
            Permission.objects.exclude(code__in=declared)
            .values_list("code", flat=True)
        )
        for code in stale:
            self.stdout.write(self.style.WARNING(f"Stale permission (kept): {code}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Permissions synced: {created} created, {updated} updated."
            )
        )
