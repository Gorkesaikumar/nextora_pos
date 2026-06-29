"""Export ALL data for a single tenant to a portable JSON archive.

Use cases: GDPR data export, tenant offboarding, and migrating a tenant to a
new shard (export here -> import_tenant on the target).

Reads under bypass_tenant() because this is a deliberate, audited cross-tenant
operation; it must be run with the nextora_admin (BYPASSRLS) DB role so RLS does
not hide the rows.

Models are serialized in FK-dependency order so the archive re-imports cleanly.
"""
import uuid

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError

from shared.tenancy.context import bypass_tenant


def _tenant_models():
    """Tenant-scoped models, naive FK-dependency ordered (parents first)."""
    models = [
        m
        for m in apps.get_models()
        if "tenant_id" in {f.attname for f in m._meta.concrete_fields}
    ]
    # Sort so a model appears after models it FKs to (best-effort topological).
    ordered: list = []
    seen: set = set()

    def visit(model) -> None:
        if model in seen:
            return
        seen.add(model)
        for field in model._meta.fields:
            if field.is_relation and field.related_model in models:
                visit(field.related_model)
        ordered.append(model)

    for m in models:
        visit(m)
    return ordered


class Command(BaseCommand):
    help = "Export all data for one tenant to a JSON file."

    def add_arguments(self, parser) -> None:
        parser.add_argument("tenant_id", type=str)
        parser.add_argument("--output", required=True, help="Output .json path")

    def handle(self, *args, **options) -> None:
        try:
            tenant_id = uuid.UUID(options["tenant_id"])
        except ValueError as exc:
            raise CommandError("tenant_id must be a UUID.") from exc

        objects: list = []
        with bypass_tenant():
            for model in _tenant_models():
                qs = model.all_objects.filter(tenant_id=tenant_id)
                objects.extend(qs)

        with open(options["output"], "w", encoding="utf-8") as fh:
            serializers.serialize("json", objects, stream=fh, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(objects)} rows for tenant {tenant_id} "
                f"to {options['output']}."
            )
        )
