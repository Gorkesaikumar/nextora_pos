"""Export a tenant's products to a CSV file (or stdout)."""
import uuid

from django.core.management.base import BaseCommand, CommandError

from contexts.catalog.services.import_export import export_products_csv
from shared.tenancy import tenant_scope


class Command(BaseCommand):
    help = "Bulk-export a tenant's products to CSV."

    def add_arguments(self, parser) -> None:
        parser.add_argument("tenant_id", type=str)
        parser.add_argument("--file", help="Output path; omit to print to stdout.")

    def handle(self, *args, **options) -> None:
        try:
            tenant_id = uuid.UUID(options["tenant_id"])
        except ValueError as exc:
            raise CommandError("tenant_id must be a UUID.") from exc

        with tenant_scope(tenant_id):
            csv_text = export_products_csv()

        if options.get("file"):
            with open(options["file"], "w", encoding="utf-8", newline="") as fh:
                fh.write(csv_text)
            self.stdout.write(self.style.SUCCESS(f"Exported to {options['file']}."))
        else:
            self.stdout.write(csv_text)
