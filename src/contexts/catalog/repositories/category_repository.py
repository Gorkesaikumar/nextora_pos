"""Data access for the Category tree."""
import uuid
from collections.abc import Iterator

from django.db import models

from contexts.catalog.models import Category

from .base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def roots(self) -> models.QuerySet[Category]:
        return self.get_queryset().filter(parent__isnull=True)

    def children_of(self, category_id: uuid.UUID) -> models.QuerySet[Category]:
        return self.get_queryset().filter(parent_id=category_id)

    def ancestors(self, category: Category) -> Iterator[Category]:
        """Yield ancestors from immediate parent up to the root.

        Walks ``parent`` links; used by the cycle guard when reparenting.
        """
        node = category.parent
        while node is not None:
            yield node
            node = node.parent

    def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        qs = self.get_queryset().filter(slug=slug)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()
