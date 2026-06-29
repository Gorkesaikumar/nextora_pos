"""Apply PostgreSQL Row-Level Security to every tenant-scoped table.

For each model that has a concrete ``tenant_id`` column, this:
  1. ENABLE + FORCE ROW LEVEL SECURITY (FORCE => even the table owner obeys it),
  2. creates an isolation policy comparing tenant_id to the session GUC
     ``app.current_tenant`` (set per-request by the tenant middleware).

current_setting(..., true) returns NULL when unset, so with no tenant bound the
predicate is false and NO rows are visible — fail closed.

Idempotent: safe to re-run. In production the generated SQL is committed as a
RunSQL migration; this command is the generator and a dev convenience.

Run as the nextora_admin (BYPASSRLS) role. The application connects as
nextora_app, which is SUBJECT to these policies.
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

POLICY_NAME = "tenant_isolation"


def _tenant_tables() -> list[str]:
    tables = []
    for model in apps.get_models():
        field_names = {f.attname for f in model._meta.concrete_fields}
        # RBAC tables (Role, Membership) carry a NULLABLE tenant_id (NULL =
        # platform scope). The RLS predicate would hide those platform rows, so
        # they opt out via __rls_exempt__ and are tenant-scoped in app queries.
        if getattr(model, "__rls_exempt__", False):
            continue
        if "tenant_id" in field_names and not model._meta.abstract:
            tables.append(model._meta.db_table)
    return sorted(set(tables))


class Command(BaseCommand):
    help = "Enable/refresh RLS isolation policies on all tenant-scoped tables."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the SQL without executing it.",
        )

    def handle(self, *args, **options) -> None:
        dry = options["dry_run"]
        statements: list[str] = []

        for table in _tenant_tables():
            statements += [
                f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;',
                f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;',
                f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";',
                (
                    f"CREATE POLICY {POLICY_NAME} ON \"{table}\"\n"
                    f"  USING (tenant_id = "
                    f"current_setting('app.current_tenant', true)::uuid)\n"
                    f"  WITH CHECK (tenant_id = "
                    f"current_setting('app.current_tenant', true)::uuid);"
                ),
            ]

        sql = "\n".join(statements)
        if dry:
            self.stdout.write(sql or "-- no tenant tables found")
            return

        if not statements:
            self.stdout.write("No tenant-scoped tables found.")
            return

        with connection.cursor() as cursor:
            cursor.execute(sql)
        self.stdout.write(
            self.style.SUCCESS(f"RLS applied to {len(_tenant_tables())} tables.")
        )
