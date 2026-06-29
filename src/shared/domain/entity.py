"""Entity / AggregateRoot base classes — pure Python, no Django.

Entities have identity and a lifecycle; equality is by id, not by attributes.
Aggregate roots additionally record domain events to be published (via the
transactional outbox) once their changes are committed.
"""
import uuid
from typing import Any


class Entity:
    """Has identity. Two entities are equal iff their ids are equal."""

    def __init__(self, id: uuid.UUID | None = None) -> None:
        self.id = id or uuid.uuid4()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity):
    """Consistency boundary + source of domain events.

    Business operations append events via ``record_event``; the application
    service collects ``pull_events`` after a successful commit and hands them to
    the outbox for reliable, at-least-once publication.
    """

    def __init__(self, id: uuid.UUID | None = None) -> None:
        super().__init__(id)
        self._events: list[Any] = []

    def record_event(self, event: Any) -> None:
        self._events.append(event)

    def pull_events(self) -> list[Any]:
        events, self._events = self._events, []
        return events
