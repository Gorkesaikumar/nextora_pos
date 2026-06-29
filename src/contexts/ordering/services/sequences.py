"""Concurrency-safe, daily-reset numbering.

next_number locks the counter row (SELECT ... FOR UPDATE) so two terminals
issuing a number at the same instant serialise and never produce a duplicate.
A new date creates a fresh counter row, giving automatic daily reset.
"""
import uuid
from datetime import date

from django.db import transaction
from django.utils import timezone

from contexts.ordering.models import DailyCounter


def next_number(
    location_id: uuid.UUID | None,
    scope: str,
    *,
    series: str = "",
    on: date | None = None,
) -> int:
    on = on or timezone.localdate()
    with transaction.atomic():
        counter, _ = DailyCounter.objects.get_or_create(
            location_id=location_id, scope=scope, series=series, date=on
        )
        counter = DailyCounter.objects.select_for_update().get(pk=counter.pk)
        counter.last_number += 1
        counter.save(update_fields=["last_number", "updated_at"])
        return counter.last_number
