"""Data access for suppliers."""
import uuid

from django.db import models

from contexts.inventory.models import Supplier

from .base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    def active(self) -> models.QuerySet[Supplier]:
        return self.get_queryset().filter(is_active=True)

    def code_exists(self, code: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        if not code:
            return False
        qs = self.get_queryset().filter(code=code)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()
