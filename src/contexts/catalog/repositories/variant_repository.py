"""Data access for product variants."""
import uuid

from django.db import models

from contexts.catalog.models import ProductVariant

from .base import BaseRepository


class ProductVariantRepository(BaseRepository[ProductVariant]):
    model = ProductVariant

    def for_product(self, product_id: uuid.UUID) -> models.QuerySet[ProductVariant]:
        return self.get_queryset().filter(product_id=product_id, is_active=True)

    def default_for_product(self, product_id: uuid.UUID) -> ProductVariant | None:
        return (
            self.get_queryset()
            .filter(product_id=product_id, is_default=True)
            .first()
        )

    def sku_exists(self, sku: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        qs = self.get_queryset().filter(sku=sku)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()
