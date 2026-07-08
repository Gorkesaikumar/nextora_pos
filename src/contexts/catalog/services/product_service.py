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
from contexts.catalog.models.modifier import ProductModifierGroup
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


def _set_modifier_groups(product: Product, mod_groups) -> None:
    """Assign modifier groups to a product via the through table.

    Django's default M2M ``.set()`` issues a raw INSERT that skips
    ``TenantAwareModel.save()``, so ``tenant_id`` is never stamped and the DB
    raises a NOT NULL constraint.  We manually manage the through-model rows
    instead.
    """
    from shared.tenancy.context import bypass_tenant

    tenant_id = product.tenant_id
    group_ids = {g.pk if hasattr(g, "pk") else g for g in mod_groups}

    with bypass_tenant():
        # Soft-delete links that are no longer selected.
        ProductModifierGroup.objects.filter(
            product=product
        ).exclude(group_id__in=group_ids).update(is_deleted=True)

        # Find which groups are already linked (active or soft-deleted).
        existing_map = {
            str(row["group_id"]): row["is_deleted"]
            for row in ProductModifierGroup.objects.filter(
                product=product, group_id__in=group_ids
            ).values("group_id", "is_deleted")
        }

        new_links = []
        restore_ids = []
        for gid in group_ids:
            key = str(gid)
            if key not in existing_map:
                new_links.append(
                    ProductModifierGroup(
                        product=product,
                        group_id=gid,
                        tenant_id=tenant_id,
                        is_deleted=False,
                    )
                )
            elif existing_map[key]:  # was soft-deleted, restore it
                restore_ids.append(gid)

        if new_links:
            ProductModifierGroup.objects.bulk_create(new_links)
        if restore_ids:
            ProductModifierGroup.objects.filter(
                product=product, group_id__in=restore_ids
            ).update(is_deleted=False)


@transaction.atomic
def create_product(data: dict[str, Any]) -> Product:
    mod_groups = data.pop("modifier_groups", None)
    validate_new_product(data, repo=_products)

    product = _products.add(Product(**data))
    if mod_groups is not None:
        _set_modifier_groups(product, mod_groups)

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

    mod_groups = changes.pop("modifier_groups", None)
    validate_product_changes(product_id, changes, repo=_products)

    before = _snapshot(product)
    for field, value in changes.items():
        setattr(product, field, value)
    _products.save(product)
    if mod_groups is not None:
        _set_modifier_groups(product, mod_groups)

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
