"""Pure tests for billing period arithmetic (no DB)."""
from datetime import datetime

from contexts.billing.domain.enums import BillingInterval
from contexts.billing.domain.periods import add_interval, add_months, month_key


def test_add_months_simple():
    assert add_months(datetime(2026, 1, 15), 1) == datetime(2026, 2, 15)


def test_add_months_clamps_to_month_end():
    # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year).
    assert add_months(datetime(2026, 1, 31), 1) == datetime(2026, 2, 28)


def test_add_months_crosses_year():
    assert add_months(datetime(2026, 12, 10), 1) == datetime(2027, 1, 10)


def test_add_interval_monthly_quarterly_yearly():
    start = datetime(2026, 3, 10)
    assert add_interval(start, BillingInterval.MONTHLY) == datetime(2026, 4, 10)
    assert add_interval(start, BillingInterval.QUARTERLY) == datetime(2026, 6, 10)
    assert add_interval(start, BillingInterval.YEARLY) == datetime(2027, 3, 10)


def test_month_key_format():
    assert month_key(datetime(2026, 6, 5)) == "2026-06"
