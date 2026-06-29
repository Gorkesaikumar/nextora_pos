"""InventoryItem setup service — provisioning stock records and reorder levels.

An InventoryItem is the master stock record for a product in a warehouse. It is
created lazily (the first time a product is stocked in a warehouse) and is the
record the catalog links to via ``product.inventory_item_id``.
"""
import uuid
from decimal import Decimal
from typing import Any

from django.db import transaction

from contexts.inventory.exceptions import InventoryItemNotFound
from contexts.inventory.models import InventoryItem
from contexts.inventory.repositories import InventoryItemRepository

_items = InventoryItemRepository()


@transaction.atomic
def ensure_item(
    *,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_sku: str,
    product_name: str,
    minimum_stock: Decimal = Decimal("0"),
    reorder_point: Decimal = Decimal("0"),
    reorder_quantity: Decimal = Decimal("0"),
) -> InventoryItem:
    """Get the stock record for (product, warehouse), creating it if absent.

    Idempotent: safe to call whenever a product is first stocked in a warehouse.
    """
    existing = _items.get_for_product_warehouse(product_id, warehouse_id)
    if existing is not None:
        return existing

    item = InventoryItem(
        product_id=product_id,
        warehouse_id=warehouse_id,
        product_sku=product_sku,
        product_name=product_name,
        minimum_stock=minimum_stock,
        reorder_point=reorder_point,
        reorder_quantity=reorder_quantity,
    )
    return _items.add(item)


@transaction.atomic
def set_reorder_levels(
    item_id: uuid.UUID,
    *,
    minimum_stock: Decimal | None = None,
    reorder_point: Decimal | None = None,
    reorder_quantity: Decimal | None = None,
) -> InventoryItem:
    item = _items.lock(item_id)
    if item is None:
        raise InventoryItemNotFound(str(item_id))

    fields: dict[str, Any] = {}
    if minimum_stock is not None:
        fields["minimum_stock"] = minimum_stock
    if reorder_point is not None:
        fields["reorder_point"] = reorder_point
    if reorder_quantity is not None:
        fields["reorder_quantity"] = reorder_quantity

    if fields:
        for field, value in fields.items():
            setattr(item, field, value)
        # auto_now keeps updated_at fresh; include it in the partial update.
        _items.save(item, update_fields=[*fields.keys(), "updated_at"])
    return item
