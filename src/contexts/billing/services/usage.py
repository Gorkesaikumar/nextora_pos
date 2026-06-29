"""Usage tracking + limit enforcement.

Two metric kinds:
  * live providers — a callable that counts a resource on demand (branches,
    employees). Registered by the owning context so billing stays decoupled.
  * counters — UsageCounter rows we increment (storage, invoices-per-month).

enforce_limit() is the guardrail other contexts call before a constrained action.
"""
import uuid
from collections.abc import Callable

from django.db import transaction
from django.db.models import F

from contexts.billing.domain import metrics
from contexts.billing.exceptions import LimitExceeded
from contexts.billing.models import UsageCounter
from contexts.billing.services import entitlements
from shared.tenancy import tenant_scope

# metric -> callable(tenant_id) -> current count
_PROVIDERS: dict[str, Callable[[uuid.UUID], int]] = {}


def register_provider(metric: str, fn: Callable[[uuid.UUID], int]) -> None:
    _PROVIDERS[metric] = fn


def current_usage(tenant_id: uuid.UUID, metric: str, period_key: str = "") -> int:
    provider = _PROVIDERS.get(metric)
    if provider is not None:
        return provider(tenant_id)
    with tenant_scope(tenant_id):
        row = UsageCounter.objects.filter(
            metric=metric, period_key=period_key
        ).first()
        return row.value if row else 0


def increment(
    tenant_id: uuid.UUID, metric: str, by: int = 1, period_key: str = ""
) -> int:
    with tenant_scope(tenant_id), transaction.atomic():
        obj, _ = UsageCounter.objects.get_or_create(
            metric=metric, period_key=period_key
        )
        UsageCounter.objects.filter(pk=obj.pk).update(value=F("value") + by)
        obj.refresh_from_db(fields=["value"])
        return obj.value


def check_limit(
    tenant_id: uuid.UUID, metric: str, by: int = 1, period_key: str = ""
) -> bool:
    limit = entitlements.get_limit(tenant_id, metric)
    if limit is None:  # unlimited
        return True
    return current_usage(tenant_id, metric, period_key) + by <= limit


def enforce_limit(
    tenant_id: uuid.UUID, metric: str, by: int = 1, period_key: str = ""
) -> None:
    limit = entitlements.get_limit(tenant_id, metric)
    if limit is None:  # unlimited
        return
    current = current_usage(tenant_id, metric, period_key)
    if current + by > limit:
        raise LimitExceeded(metric, limit, current, by)


# Convenience for the periodic invoice metric.
def month_key_now() -> str:
    from django.utils import timezone

    from contexts.billing.domain.periods import month_key

    return month_key(timezone.now())


__all__ = [
    "check_limit",
    "current_usage",
    "enforce_limit",
    "increment",
    "metrics",
    "month_key_now",
    "register_provider",
]
