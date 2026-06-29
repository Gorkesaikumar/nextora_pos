"""Celery tasks for billing. Scheduled via Celery Beat (see settings)."""
from celery import shared_task


@shared_task(name="billing.run_billing_cycle", queue="bulk")
def run_billing_cycle_task() -> int:
    """Advance all subscriptions through time-based transitions."""
    from contexts.billing.services.lifecycle import run_billing_cycle

    return run_billing_cycle()
