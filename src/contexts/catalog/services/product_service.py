"""Product write operations: validation, persistence, audit and events.

Runs within the current tenant context (set by the request middleware or by a
caller's ``tenant_scope``). The service orchestrates the use case but delegates:

  * **data access** to repositories (``contexts.catalog.repositories``),
  * **input rules** to validators (``contexts.catalog.validation``),
  * **side-effect notification** to domain events (``contexts.catalog.events``).

Every mutation is atomic; the audit row and the outbox event are written inside
the same transaction as the business change, so they can never diverge from it.
"""
import uuid
from decimal import Decimal
from typing import Any

from django.db import transaction

from contexts.audit.services import record_audit
from contexts.catalog.events import (
    publish_product_created,
    publish_product_deleted,
    publish_product_updated,
)
from contexts.catalog.exceptions import ProductNotFound
from contexts.catalog.models import Category, KitchenStation, Printer, Product
from contexts.catalog.repositories import CategoryRepository, ProductRepository
from contexts.catalog.validation import (
    validate_new_product,
    validate_product_changes,
    validate_reparent,
)

_products = ProductRepository()
_categories = CategoryRepository()

_AUDITED_FIELDS = (
    "name", "sku", "barcode", "hsn_code", "base_price", "currency",
    "type", "is_active", "category_id", "tax_class_id",
)


def _snapshot(product: Product) -> dict[str, Any]:
    return {f: _json_safe(getattr(product, f)) for f in _AUDITED_FIELDS}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    return value


@transaction.atomic
def create_product(data: dict[str, Any]) -> Product:
    validate_new_product(data, repo=_products)

    product = _products.add(Product(**data))

    record_audit(
        "product.created",
        entity_type="product",
        entity_id=product.id,
        new_value=_snapshot(product),
    )
    publish_product_created(product)
    return product


@transaction.atomic
def update_product(product_id: uuid.UUID, changes: dict[str, Any]) -> Product:
    product = _products.get(product_id)
    if product is None:
        raise ProductNotFound(str(product_id))

    validate_product_changes(product_id, changes, repo=_products)

    before = _snapshot(product)
    for field, value in changes.items():
        setattr(product, field, value)
    _products.save(product)

    after = _snapshot(product)
    diff = {k: {"from": before[k], "to": after[k]}
            for k in after if before.get(k) != after.get(k)}

    record_audit(
        "product.updated",
        entity_type="product",
        entity_id=product.id,
        old_value=before,
        new_value=diff,
    )
    publish_product_updated(product, diff)
    return product


@transaction.atomic
def delete_product(product_id: uuid.UUID) -> None:
    product = _products.get(product_id)
    if product is None:
        raise ProductNotFound(str(product_id))

    sku = product.sku
    _products.soft_delete(product)  # soft delete (TenantAwareModel)

    record_audit("product.deleted", entity_type="product", entity_id=product_id)
    publish_product_deleted(product_id, sku)


def set_category_parent(category: Category, parent: Category | None) -> Category:
    """Reparent a category, refusing cycles (a node can't be its own ancestor)."""
    validate_reparent(category, parent, repo=_categories)
    category.parent = parent
    category.save(update_fields=["parent", "updated_at"])
    return category


def resolve_routing(product: Product) -> tuple[Printer | None, KitchenStation | None]:
    """Effective (printer, kitchen_station) for a product.

    A product-level override wins; otherwise the value is inherited from the
    category, whose routing targets are held as UUID soft references
    (``printer_id`` / ``station_id``) and resolved to instances here.
    """
    category = product.category
    printer = product.printer
    if printer is None and category and category.printer_id:
        printer = Printer.objects.filter(id=category.printer_id).first()

    station = product.kitchen_station
    if station is None and category and category.station_id:
        station = KitchenStation.objects.filter(id=category.station_id).first()

    return printer, station
