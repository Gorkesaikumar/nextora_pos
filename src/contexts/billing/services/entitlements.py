"""Entitlements — resolve a tenant's active plan and its limits.

The only place that answers "what is this tenant allowed to do". Reads the
active subscription -> plan. A tenant with no live subscription gets a zero
allowance (deny), never unlimited.
"""
import uuid

from contexts.billing.domain import metrics
from contexts.billing.domain.enums import SubscriptionStatus
from contexts.billing.models import Plan, Subscription
from shared.tenancy import tenant_scope

# metric -> Plan column holding its limit (NULL = unlimited).
_LIMIT_FIELDS = {
    metrics.BRANCHES: "max_branches",
    metrics.EMPLOYEES: "max_employees",
    metrics.INVOICES: "max_invoices_per_month",
    metrics.STORAGE_MB: "max_storage_mb",
}


def get_active_subscription(tenant_id: uuid.UUID) -> Subscription | None:
    with tenant_scope(tenant_id):
        return (
            Subscription.objects.filter(
                status__in=SubscriptionStatus.occupied()
            )
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )


def get_plan(tenant_id: uuid.UUID) -> Plan | None:
    sub = get_active_subscription(tenant_id)
    return sub.plan if sub else None


def get_limit(tenant_id: uuid.UUID, metric: str) -> int | None:
    """Return the numeric limit, None if unlimited, or 0 if no subscription."""
    plan = get_plan(tenant_id)
    if plan is None:
        return 0
    return getattr(plan, _LIMIT_FIELDS[metric])


def has_feature(tenant_id: uuid.UUID, key: str) -> bool:
    plan = get_plan(tenant_id)
    return bool(plan and plan.features.get(key))
