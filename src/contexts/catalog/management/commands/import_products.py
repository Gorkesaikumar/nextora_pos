"""Import products from a CSV file for a given tenant."""
import uuid

from django.core.management.base import BaseCommand, CommandError

from contexts.catalog.services.import_export import import_products_csv
from shared.tenancy import tenant_scope


class Command(BaseCommand):
    help = "Bulk-import products from CSV into a tenant."

    def add_arguments(self, parser) -> None:
        parser.add_argument("tenant_id", type=str)
        parser.add_argument("--file", required=True)

    def handle(self, *args, **options) -> None:
        try:
            tenant_id = uuid.UUID(options["tenant_id"])
        except ValueError as exc:
            raise CommandError("tenant_id must be a UUID.") from exc

        with open(options["file"], encoding="utf-8") as fh:
            text = fh.read()

        with tenant_scope(tenant_id):
            report = import_products_csv(text)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {report.created}, updated {report.updated}, "
                f"errors {len(report.errors)}."
            )
        )
        for err in report.errors:
            self.stdout.write(self.style.WARNING(f"  line {err['line']}: {err['error']}"))
