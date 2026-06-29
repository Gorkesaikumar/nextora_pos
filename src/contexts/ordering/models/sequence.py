"""Daily-reset counters for order / KOT / invoice numbers (tenant + branch).

One row per (tenant, location, scope, series, date). Because the date is part of
the key, counters reset every day automatically. Numbers are issued under a
SELECT ... FOR UPDATE row lock, so concurrent terminals never collide.
"""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class DailyCounter(TenantAwareModel):
    location_id = models.UUIDField(null=True, blank=True)
    scope = models.CharField(max_length=20)        # "order" | "kot" | "invoice"
    series = models.CharField(max_length=20, blank=True)
    date = models.DateField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "daily_counter"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "location_id", "scope", "series", "date"],
                name="uq_daily_counter__key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scope}:{self.date}:{self.last_number}"
