"""Usage tracking counters (tenant-scoped).

For metrics we increment ourselves (storage, invoices-per-month). Live-count
metrics (branches, employees) are computed by usage providers instead and don't
store a counter.

period_key = "" for absolute metrics, "YYYY-MM" for monthly metrics.
"""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class UsageCounter(TenantAwareModel):
    metric = models.CharField(max_length=50)
    period_key = models.CharField(max_length=10, default="", blank=True)
    value = models.BigIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "usage_counter"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "metric", "period_key"],
                name="uq_usage_counter__tenant_metric_period",
            ),
            models.CheckConstraint(
                check=models.Q(value__gte=0), name="ck_usage_counter__nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.metric}[{self.period_key}]={self.value}"
