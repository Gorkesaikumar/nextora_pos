"""Billing period arithmetic — pure functions, no Django, no external deps.

Month-aware addition that clamps the day to the target month's last day
(e.g. Jan 31 + 1 month -> Feb 28/29), which is the correct behaviour for
billing anniversaries.
"""
import calendar
from datetime import datetime

from .enums import BillingInterval

_MONTHS = {
    BillingInterval.MONTHLY: 1,
    BillingInterval.QUARTERLY: 3,
    BillingInterval.YEARLY: 12,
}


def add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def add_interval(dt: datetime, interval: str) -> datetime:
    return add_months(dt, _MONTHS[BillingInterval(interval)])


def month_key(dt: datetime) -> str:
    """Period key for monthly usage metrics, e.g. '2026-06'."""
    return f"{dt.year:04d}-{dt.month:02d}"
