import dataclasses
import logging
import uuid
from datetime import datetime

from django.db import transaction

from shared.domain.events import DomainEvent
from shared.infrastructure.events.models import OutboxEvent

logger = logging.getLogger(__name__)


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
    Event Dispatcher.

    Handles storing DomainEvents in the Transactional Outbox and triggering
    the async processing via Celery on transaction commit.

    If the Celery broker (Redis) is unavailable the error is logged as a
    warning — the OutboxEvent row is already persisted, so the periodic
    ``process_outbox_sweep`` beat task will retry delivery once the broker
    comes back online.
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

    def _trigger_celery():
        try:
            dispatch_event_to_handlers.delay(str(outbox_event.id))
        except Exception as exc:  # noqa: BLE001  (broker unavailable)
            logger.warning(
                "Celery broker unavailable — OutboxEvent %s will be retried "
                "by the sweep task. Error: %s",
                outbox_event.id,
                exc,
            )

    # Trigger Celery task only if the transaction commits successfully
    transaction.on_commit(_trigger_celery)

