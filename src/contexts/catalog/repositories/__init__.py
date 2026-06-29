"""Repository layer for the catalog context.

Repositories encapsulate **all** ORM access for catalog aggregates so the
service layer stays free of query construction (no `.objects.filter(...)` in
services). Every query runs through the tenant-scoped managers, so repositories
never juggle ``tenant_id`` directly — the active tenant context (set by the
request middleware or a ``tenant_scope``) decides what is visible. This is
fail-closed: with no tenant in context the managers return an empty queryset
rather than another tenant's rows.
"""
from .category_repository import CategoryRepository
from .product_repository import ProductRepository
from .variant_repository import ProductVariantRepository

__all__ = [
    "CategoryRepository",
    "ProductRepository",
    "ProductVariantRepository",
]
