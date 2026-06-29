"""Celery background tasks for the Inventory context."""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="inventory.scan_expiring_batches",
    max_retries=3,
    default_retry_delay=300,
    queue="bulk",
)
def scan_expiring_batches_task(self, days_ahead: int = 30) -> dict:
    """
    Scans all batches expiring within `days_ahead` days and creates alerts.
    Should run daily (e.g., every morning at 06:00).
    """
    from contexts.inventory.services import scan_expiring_batches
    try:
        count = scan_expiring_batches(days_ahead=days_ahead)
        logger.info(f"Expiry scan complete. New alerts created: {count}")
        return {"alerts_created": count}
    except Exception as exc:
        logger.error(f"Expiry scan failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="inventory.scan_low_stock",
    max_retries=3,
    default_retry_delay=300,
    queue="bulk",
)
def scan_low_stock_task(self) -> dict:
    """
    Scans all inventory items for low/out-of-stock conditions.
    Should run every 15–30 minutes or after significant stock events.
    """
    from contexts.inventory.services import scan_low_stock_items
    try:
        count = scan_low_stock_items()
        logger.info(f"Low-stock scan complete. New alerts created: {count}")
        return {"alerts_created": count}
    except Exception as exc:
        logger.error(f"Low-stock scan failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
