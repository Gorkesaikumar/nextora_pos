"""Celery tasks for Domain Event async processing."""

import importlib
import logging
import traceback
from datetime import timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import IntegrityError, transaction
from django.utils import timezone

from shared.infrastructure.events.models import (
    DeadLetterEvent,
    EventConsumption,
    OutboxEvent,
    OutboxEventStatus,
)
from shared.infrastructure.events.registry import get_handlers

logger = logging.getLogger(__name__)


@shared_task(queue="default")
def process_outbox_sweep():
    """Beat task to sweep for orphaned pending or stuck in-progress events.
    
    This handles race conditions or if a worker crashes before on_commit
    could trigger dispatch_event_to_handlers.
    """
    # Pick events that are stuck in PENDING or IN_PROGRESS for more than 1 minute
    threshold = timezone.now() - timedelta(minutes=1)
    stuck_events = OutboxEvent.objects.filter(
        status__in=[OutboxEventStatus.PENDING, OutboxEventStatus.IN_PROGRESS],
        created_at__lt=threshold
    )

    for event in stuck_events:
        dispatch_event_to_handlers.delay(str(event.id))


@shared_task(queue="default")
def dispatch_event_to_handlers(outbox_event_id: str):
    """Marks outbox event as IN_PROGRESS and queues individual handlers."""
    try:
        outbox_event = OutboxEvent.objects.get(id=outbox_event_id)
    except OutboxEvent.DoesNotExist:
        logger.warning(f"OutboxEvent {outbox_event_id} not found.")
        return

    # Skip if already processed or in progress
    if outbox_event.status in (OutboxEventStatus.IN_PROGRESS, OutboxEventStatus.PROCESSED):
        return

    # Use select_for_update to prevent concurrent dispatch
    with transaction.atomic():
        outbox_event = OutboxEvent.objects.select_for_update().get(id=outbox_event_id)
        if outbox_event.status in (OutboxEventStatus.IN_PROGRESS, OutboxEventStatus.PROCESSED):
            return
            
        outbox_event.status = OutboxEventStatus.IN_PROGRESS
        outbox_event.save(update_fields=["status", "updated_at"])

    handlers = get_handlers(outbox_event.event_type)
    
    # Trigger a specific execution task for each handler
    for handler_func in handlers:
        handler_path = f"{handler_func.__module__}.{handler_func.__name__}"
        execute_handler.delay(outbox_event_id, handler_path)

    # Mark as successfully dispatched to queues (PROCESSED)
    outbox_event.status = OutboxEventStatus.PROCESSED
    outbox_event.save(update_fields=["status", "updated_at"])


@shared_task(bind=True, queue="default", max_retries=5, default_retry_delay=60)
def execute_handler(self, outbox_event_id: str, handler_path: str):
    """Executes a single event handler idempotently with retries."""
    try:
        outbox_event = OutboxEvent.objects.get(id=outbox_event_id)
    except OutboxEvent.DoesNotExist:
        logger.error(f"OutboxEvent {outbox_event_id} not found during execution.")
        return

    # 1. Idempotency Check
    try:
        with transaction.atomic():
            EventConsumption.objects.create(
                event_id=outbox_event_id, handler_name=handler_path
            )
    except IntegrityError:
        # Already processed successfully
        logger.info(f"Idempotent skip: {handler_path} already processed {outbox_event_id}")
        return

    # 2. Execute Business Logic
    try:
        # Dynamically import the handler
        module_name, func_name = handler_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        handler_func = getattr(module, func_name)

        # Execute handler with payload
        # Passing payload directly instead of the reconstructed event object for simplicity
        # Handlers should be designed to accept dictionary payloads.
        handler_func(outbox_event.payload)

    except Exception as exc:
        # Execution failed, rollback idempotency record
        EventConsumption.objects.filter(
            event_id=outbox_event_id, handler_name=handler_path
        ).delete()
        
        try:
            # Exponential backoff (60s, 120s, 240s...)
            countdown = self.default_retry_delay * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            # 3. Dead Letter Queue
            DeadLetterEvent.objects.create(
                event_id=outbox_event_id,
                tenant_id=outbox_event.tenant_id,
                event_type=outbox_event.event_type,
                handler_name=handler_path,
                error_message=str(exc),
                stack_trace=traceback.format_exc()
            )
            logger.error(f"Event {outbox_event_id} handler {handler_path} sent to DLQ.")
