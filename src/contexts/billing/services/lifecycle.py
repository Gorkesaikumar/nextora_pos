"""Time-based subscription transitions, driven by Celery Beat.

Pushes subscriptions through the state machine:
  * TRIALING whose trial ended  -> PAST_DUE (+grace) and issue the first invoice
  * ACTIVE whose period ended   -> renew (PAST_DUE + invoice) or EXPIRE
  * PAST_DUE past its grace      -> EXPIRED
  * CANCELED past its period     -> EXPIRED

Payment success (webhook / mark_paid) handles the forward transitions back to
ACTIVE. This function only handles the passage of time.
"""
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from contexts.billing.domain.enums import SubscriptionStatus
from contexts.billing.domain.periods import add_interval
from contexts.billing.models import Subscription
from contexts.billing.services import invoice_service
from shared.tenancy import bypass_tenant, tenant_scope


def run_billing_cycle(now: datetime | None = None, *, batch_size: int = 1000) -> int:
    """Advance time-based subscription transitions.

    Each subscription is processed in its own transaction with a row lock, so:
      * a crash/retry can never double-invoice (atomic status change + invoice),
      * two overlapping beat runs cannot both process the same subscription.

    Ids are fetched in batches under bypass (cross-tenant), then each is
    processed under its own tenant scope.
    """
    now = now or timezone.now()
    processed = 0
    last_seen = None

    while True:
        with bypass_tenant():
            qs = Subscription.all_objects.filter(
                status__in=SubscriptionStatus.occupied(), is_deleted=False
            ).order_by("id")
            if last_seen is not None:
                qs = qs.filter(id__gt=last_seen)
            batch = list(qs.values_list("id", "tenant_id")[:batch_size])

        if not batch:
            break

        for sub_id, tenant_id in batch:
            last_seen = sub_id
            with tenant_scope(tenant_id), transaction.atomic():
                sub = (
                    Subscription.objects.select_for_update()
                    .select_related("plan")
                    .get(id=sub_id)
                )
                if _process(sub, now):
                    processed += 1

        if len(batch) < batch_size:
            break
    return processed


def _open_renewal(sub: Subscription, period_start: datetime, now: datetime) -> None:
    period_end = add_interval(period_start, sub.interval)
    sub.status = SubscriptionStatus.PAST_DUE
    sub.current_period_start = period_start
    sub.current_period_end = period_end
    sub.grace_until = period_start + timedelta(days=sub.plan.grace_days)
    sub.save(update_fields=[
        "status", "current_period_start", "current_period_end",
        "grace_until", "updated_at",
    ])
    invoice_service.generate_invoice(
        sub.tenant_id, sub, period_start, period_end, now
    )


def _expire(sub: Subscription) -> None:
    sub.status = SubscriptionStatus.EXPIRED
    sub.save(update_fields=["status", "updated_at"])


def _process(sub: Subscription, now: datetime) -> bool:
    if sub.status == SubscriptionStatus.TRIALING and sub.trial_end and sub.trial_end <= now:
        _open_renewal(sub, sub.trial_end, now)
        return True

    if sub.status == SubscriptionStatus.ACTIVE and sub.current_period_end <= now:
        if sub.auto_renew:
            _open_renewal(sub, sub.current_period_end, now)
        else:
            _expire(sub)
        return True

    if (
        sub.status == SubscriptionStatus.PAST_DUE
        and sub.grace_until is not None
        and sub.grace_until <= now
    ):
        _expire(sub)
        return True

    if sub.status == SubscriptionStatus.CANCELED and sub.current_period_end <= now:
        _expire(sub)
        return True

    return False
