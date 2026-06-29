"""Data access for warehouses."""
import uuid

from django.db import models

from contexts.inventory.models import Warehouse

from .base import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    model = Warehouse

    def active(self) -> models.QuerySet[Warehouse]:
        return self.get_queryset().filter(is_active=True)

    def for_branch(self, branch_id: uuid.UUID) -> models.QuerySet[Warehouse]:
        return self.get_queryset().filter(branch_id=branch_id, is_active=True)

    def default_for_branch(self, branch_id: uuid.UUID | None) -> Warehouse | None:
        """Resolve the default warehouse to deduct a sale from.

        Note: the current ``is_default`` uniqueness is per-tenant (see ADR-0001
        review W3); branch-scoped defaults need the constraint widened to
        ``(tenant, branch_id)`` before this is fully correct for multi-branch.
        """
        qs = self.get_queryset().filter(is_default=True, is_active=True)
        if branch_id is not None:
            branch_default = qs.filter(branch_id=branch_id).first()
            if branch_default is not None:
                return branch_default
        return qs.first()

    def code_exists(self, code: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        qs = self.get_queryset().filter(code=code)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()
