"""Bulk CSV import / export for products.

Import is row-resilient: each row runs in its own savepoint so one bad row never
aborts the batch; a structured report is returned and a single audit summary is
written. Upsert key is SKU within the tenant.
"""
import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db import transaction

from contexts.audit.services import record_audit
from contexts.catalog.domain.enums import ProductType
from contexts.catalog.models import Category, Product, TaxClass

CSV_FIELDS = [
    "sku", "name", "category", "type", "hsn_code",
    "tax_class", "barcode", "base_price", "currency", "is_active",
]


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    errors: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


# --- Export ---------------------------------------------------------------
def _row_for(product) -> dict:
    return {
        "sku": product.sku,
        "name": product.name,
        "category": product.category.name,
        "type": product.type,
        "hsn_code": product.hsn_code,
        "tax_class": product.tax_class.name if product.tax_class else "",
        "barcode": product.barcode or "",
        "base_price": product.base_price,
        "currency": product.currency,
        "is_active": "1" if product.is_active else "0",
    }


def stream_products_csv(queryset=None):
    """Yield CSV line-by-line so large catalogs never load fully into memory."""
    if queryset is None:
        queryset = Product.objects.select_related("category", "tax_class").all()

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()
    yield buffer.getvalue()

    for product in queryset.iterator(chunk_size=500):
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(_row_for(product))
        yield buffer.getvalue()


def export_products_csv(queryset=None) -> str:
    return "".join(stream_products_csv(queryset))


# --- Import ---------------------------------------------------------------
def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def import_products_csv(text: str) -> ImportReport:
    report = ImportReport()
    reader = csv.DictReader(io.StringIO(text))

    # Preload lookups once (avoids an N+1 of category/tax queries per row).
    categories = {c.name: c for c in Category.objects.all()}
    tax_classes = {t.name: t for t in TaxClass.objects.all()}

    for line_no, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            with transaction.atomic():  # savepoint per row
                created = _upsert_row(row, categories, tax_classes)
                if created:
                    report.created += 1
                else:
                    report.updated += 1
        except Exception as exc:  # noqa: BLE001 — collect, continue
            report.errors.append({"line": line_no, "error": str(exc)})

    record_audit(
        "product.bulk_imported",
        entity_type="product",
        new_value={
            "created": report.created,
            "updated": report.updated,
            "errors": len(report.errors),
        },
    )
    return report


def _upsert_row(
    row: dict[str, str],
    categories: dict[str, Category],
    tax_classes: dict[str, TaxClass],
) -> bool:
    sku = (row.get("sku") or "").strip()
    if not sku:
        raise ValueError("Missing SKU.")

    name = (row.get("name") or "").strip()
    if not name:
        raise ValueError("Missing name.")

    category_name = (row.get("category") or "").strip()
    category = categories.get(category_name)
    if category is None:
        raise ValueError(f"Unknown category '{category_name}'.")

    tax_class = None
    tax_name = (row.get("tax_class") or "").strip()
    if tax_name:
        tax_class = tax_classes.get(tax_name)
        if tax_class is None:
            raise ValueError(f"Unknown tax class '{tax_name}'.")

    ptype = (row.get("type") or ProductType.FOOD).strip()
    if ptype not in ProductType.values:
        raise ValueError(f"Invalid type '{ptype}'.")

    try:
        base_price = Decimal((row.get("base_price") or "0").strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid base_price.") from exc

    barcode = (row.get("barcode") or "").strip() or None
    fields = {
        "name": name,
        "category": category,
        "type": ptype,
        "hsn_code": (row.get("hsn_code") or "").strip(),
        "tax_class": tax_class,
        "barcode": barcode,
        "base_price": base_price,
        "currency": (row.get("currency") or "INR").strip(),
        "is_active": _parse_bool(row.get("is_active", "1")),
    }

    product = Product.objects.filter(sku=sku).first()
    if product is None:
        Product.objects.create(sku=sku, **fields)
        return True
    for key, value in fields.items():
        setattr(product, key, value)
    product.save()
    return False
