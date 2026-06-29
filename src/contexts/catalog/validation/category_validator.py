"""Validation rules for the category tree."""
from contexts.catalog.exceptions import CategoryCycle
from contexts.catalog.models import Category
from contexts.catalog.repositories import CategoryRepository


def validate_reparent(
    category: Category,
    parent: Category | None,
    *,
    repo: CategoryRepository | None = None,
) -> None:
    """Reject a reparent that would create a cycle.

    A node may not become a descendant of itself: walking up from the proposed
    parent must never reach ``category``.
    """
    if parent is None:
        return

    repo = repo or CategoryRepository()

    if parent.id == category.id:
        raise CategoryCycle(str(category.id))
    for ancestor in repo.ancestors(parent):
        if ancestor.id == category.id:
            raise CategoryCycle(str(category.id))
