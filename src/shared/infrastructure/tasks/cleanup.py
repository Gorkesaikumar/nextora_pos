import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from shared.infrastructure.events.models import OutboxEvent, OutboxEventStatus

logger = logging.getLogger(__name__)


@shared_task(queue="bulk")
def database_cleanup_task() -> str:
    """Deletes processed transactional outbox events older than 30 days to save DB space."""
    threshold = timezone.now() - timedelta(days=30)

    events_deleted, _ = OutboxEvent.objects.filter(
        status=OutboxEventStatus.PROCESSED, created_at__lt=threshold
    ).delete()

    logger.info(f"Outbox cleanup complete. Deleted {events_deleted} old events.")
    return f"Cleanup complete. Deleted {events_deleted} processed outbox events."
