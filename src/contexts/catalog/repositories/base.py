"""Generic repository base.

Provides the small, common CRUD surface every catalog repository shares. It is
deliberately thin: repositories add domain-specific query methods (e.g.
``sku_exists``) on top of this. All access goes through the model's default
manager (``objects``), which is tenant-scoped and hides soft-deleted rows; the
unscoped ``all_objects`` manager is exposed separately for the rare callers that
must see deleted history.
"""
import uuid
from typing import Generic, TypeVar

from django.db import models

ModelT = TypeVar("ModelT", bound=models.Model)


class BaseRepository(Generic[ModelT]):
    """Base class for tenant-scoped, soft-delete-aware repositories."""

    model: type[ModelT]

    def get_queryset(self) -> models.QuerySet[ModelT]:
        """Live rows for the current tenant (soft-deleted rows excluded)."""
        return self.model.objects.all()

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Return the entity by primary key, or ``None`` if absent/deleted."""
        return self.get_queryset().filter(pk=entity_id).first()

    def exists(self, entity_id: uuid.UUID) -> bool:
        return self.get_queryset().filter(pk=entity_id).exists()

    def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity. ``save`` stamps tenant/audit fields."""
        entity.save()
        return entity

    def save(self, entity: ModelT, update_fields: list[str] | None = None) -> ModelT:
        """Persist changes to an existing entity."""
        entity.save(update_fields=update_fields)
        return entity
