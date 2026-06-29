"""Pure money helpers shared by the billing engine."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def q(value) -> Decimal:
    """Quantize to 2 decimal places, HALF_UP."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def round_to_nearest(value, step: Decimal) -> Decimal:
    """Round to the nearest ``step`` (e.g. 1.00 rupee, or 0.05)."""
    step = Decimal(step)
    if step <= 0:
        return q(value)
    units = (Decimal(value) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return q(units * step)


def financial_year(on: date) -> str:
    """Indian FY (Apr–Mar), e.g. 2026-04-01 -> '2026-2027'."""
    if on.month >= 4:
        return f"{on.year}-{on.year + 1}"
    return f"{on.year - 1}-{on.year}"
