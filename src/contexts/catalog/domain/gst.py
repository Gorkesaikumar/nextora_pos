"""GST computation — pure functions, no Django.

The CGST/SGST vs IGST split depends on place-of-supply (intra- vs inter-state),
so it is computed at sale time rather than stored on the product:

  * intra-state -> CGST = SGST = rate/2
  * inter-state -> IGST = rate

Supports tax-inclusive and tax-exclusive pricing, plus an optional cess.
All money rounded HALF_UP to 2 dp.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_TWOPLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class GstBreakup:
    taxable: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal
    total_tax: Decimal
    total: Decimal


def compute_gst(
    amount: Decimal,
    rate: Decimal,
    *,
    interstate: bool,
    cess_rate: Decimal = Decimal("0"),
    inclusive: bool = False,
) -> GstBreakup:
    """Break ``amount`` into taxable base + GST components.

    ``rate`` and ``cess_rate`` are percentages (e.g. Decimal('18')).
    """
    amount = Decimal(amount)
    rate = Decimal(rate)
    cess_rate = Decimal(cess_rate)
    combined = rate + cess_rate

    if inclusive and combined > 0:
        taxable = amount * Decimal(100) / (Decimal(100) + combined)
    else:
        taxable = amount

    cess = _q(taxable * cess_rate / Decimal(100))
    gst_amount = taxable * rate / Decimal(100)

    if interstate:
        igst = _q(gst_amount)
        cgst = sgst = Decimal("0.00")
    else:
        half = _q(gst_amount / Decimal(2))
        cgst = sgst = half
        igst = Decimal("0.00")

    taxable = _q(taxable)
    total_tax = _q(cgst + sgst + igst + cess)
    total = _q(taxable + total_tax)
    return GstBreakup(taxable, cgst, sgst, igst, cess, total_tax, total)
