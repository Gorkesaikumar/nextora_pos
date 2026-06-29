"""Data access for the Product aggregate (product + variants + images)."""
import uuid

from django.db import models

from contexts.catalog.models import Product

from .base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    # --- Reads -------------------------------------------------------------
    def with_relations(self) -> models.QuerySet[Product]:
        """Base queryset with routing/tax relations eagerly loaded.

        Used by reads that resolve routing or render menus, to avoid the N+1
        that naive per-product ``.category``/``.printer`` access would cause.
        """
        return self.get_queryset().select_related(
            "category", "tax_class", "unit", "printer", "kitchen_station"
        )

    def get_for_routing(self, product_id: uuid.UUID) -> Product | None:
        """Fetch a product with the relations needed to resolve KOT routing."""
        return self.with_relations().filter(pk=product_id).first()

    def list_for_category(self, category_id: uuid.UUID) -> models.QuerySet[Product]:
        return self.with_relations().filter(category_id=category_id, is_active=True)

    def list_for_export(self) -> models.QuerySet[Product]:
        """Streaming-friendly queryset for CSV export (ordered, eager-loaded)."""
        return self.with_relations().order_by("sku").iterator()

    def lock(self, product_id: uuid.UUID) -> Product | None:
        """Row-locked fetch for mutations that must serialize (``FOR UPDATE``)."""
        return (
            self.get_queryset().select_for_update().filter(pk=product_id).first()
        )

    # --- Uniqueness helpers (exclude soft-deleted; reusable after delete) ---
    def sku_exists(self, sku: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        qs = self.get_queryset().filter(sku=sku)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()

    def barcode_exists(
        self, barcode: str, *, exclude_id: uuid.UUID | None = None
    ) -> bool:
        if not barcode:
            return False
        qs = self.get_queryset().filter(barcode=barcode)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()

    # --- Writes ------------------------------------------------------------
    def soft_delete(self, product: Product) -> None:
        """Soft delete (TenantAwareModel marks ``is_deleted``)."""
        product.delete()
