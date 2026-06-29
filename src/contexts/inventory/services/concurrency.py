"""Transactional concurrency helpers.

Deterministic multi-row locking to avoid deadlocks: when one transaction must
lock several rows (e.g. a multi-line transfer or adjustment), every transaction
acquires the locks in the **same** order (sorted by id). Out-of-order locking
between two concurrent transactions is the classic deadlock; sorting removes it.
"""
import uuid
from collections.abc import Iterable
from typing import TypeVar

from contexts.inventory.repositories.base import BaseRepository

ModelT = TypeVar("ModelT")


def lock_in_order(
    repo: BaseRepository[ModelT], entity_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, ModelT]:
    """Lock the given rows in a stable, sorted order.

    Returns ``{id: entity}`` for the rows that exist (missing ids are skipped;
    the caller decides whether that is an error).
    """
    locked: dict[uuid.UUID, ModelT] = {}
    for entity_id in sorted(set(entity_ids), key=str):
        entity = repo.lock(entity_id)
        if entity is not None:
            locked[entity_id] = entity
    return locked
