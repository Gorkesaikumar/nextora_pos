"""Generic repository base for the inventory context.

Thin, tenant-scoped, soft-delete-aware data access. Concrete repositories add
domain-specific query methods on top. All reads go through the model's default
manager (``objects``), which is tenant-scoped and hides soft-deleted rows;
``all_objects`` is used only where deleted history must be seen.
"""
import uuid
from typing import Generic, TypeVar

from django.db import models

ModelT = TypeVar("ModelT", bound=models.Model)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def get_queryset(self) -> models.QuerySet[ModelT]:
        """Live rows for the current tenant (soft-deleted excluded)."""
        return self.model.objects.all()

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return self.get_queryset().filter(pk=entity_id).first()

    def lock(self, entity_id: uuid.UUID) -> ModelT | None:
        """Row-locked fetch (``SELECT … FOR UPDATE``) for serialized mutation.

        Must be called inside an open transaction.
        """
        return self.get_queryset().select_for_update().filter(pk=entity_id).first()

    def exists(self, entity_id: uuid.UUID) -> bool:
        return self.get_queryset().filter(pk=entity_id).exists()

    def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity. ``save`` stamps tenant/audit fields."""
        entity.save()
        return entity

    def save(self, entity: ModelT, update_fields: list[str] | None = None) -> ModelT:
        entity.save(update_fields=update_fields)
        return entity
