"""Event Dispatcher.

Handles storing DomainEvents in the Transactional Outbox and triggering
the async processing via Celery on transaction commit.
"""
import dataclasses
import uuid
from datetime import datetime

from django.db import transaction

from shared.domain.events import DomainEvent
from shared.infrastructure.events.models import OutboxEvent


def _serialize_event_payload(event: DomainEvent) -> dict:
    """Serialize the dataclass to a JSON-safe dictionary."""
    payload = dataclasses.asdict(event)
    # Convert UUIDs and datetimes to string
    for key, value in payload.items():
        if isinstance(value, uuid.UUID):
            payload[key] = str(value)
        elif isinstance(value, datetime):
            payload[key] = value.isoformat()
    return payload


def dispatch(event: DomainEvent) -> None:
    """
    Dispatch a DomainEvent.
    
    This writes the event to the OutboxEvent table within the current
    database transaction. Once the transaction commits, it triggers
    the Celery task to process the event immediately.
    """
    payload = _serialize_event_payload(event)
    
    outbox_event = OutboxEvent.objects.create(
        tenant_id=event.tenant_id,
        event_type=type(event).__name__,
        event_version=event.event_version,
        payload=payload,
    )
    
    # Import locally to avoid circular dependencies if tasks import models
    from shared.infrastructure.events.tasks import dispatch_event_to_handlers
    
    # Trigger Celery task only if the transaction commits successfully
    transaction.on_commit(lambda: dispatch_event_to_handlers.delay(str(outbox_event.id)))
