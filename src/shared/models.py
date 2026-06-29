"""Shared models.

This file ensures that Django discovers models in the shared app.
"""

from shared.infrastructure.events.models import DeadLetterEvent, EventConsumption, OutboxEvent
from shared.infrastructure.storage.models import StoredFile

__all__ = [
    "OutboxEvent",
    "EventConsumption",
    "DeadLetterEvent",
    "StoredFile",
]
