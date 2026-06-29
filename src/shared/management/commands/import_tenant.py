"""Import a tenant archive produced by ``export_tenant``.

Used to restore a tenant or land it on a new shard. Runs under bypass_tenant()
so the write-guard does not reject rows whose tenant differs from the (absent)
request context, and within a single transaction for atomicity.

Must be run with the nextora_admin (BYPASSRLS) role on the TARGET database.
"""
from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import transaction

from shared.tenancy.context import bypass_tenant


class Command(BaseCommand):
    help = "Import a tenant JSON archive into this database."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--input", required=True, help="Archive .json path")

    def handle(self, *args, **options) -> None:
        with open(options["input"], encoding="utf-8") as fh:
            payload = fh.read()

        count = 0
        with bypass_tenant(), transaction.atomic():
            for obj in serializers.deserialize("json", payload):
                obj.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} rows."))
