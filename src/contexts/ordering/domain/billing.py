"""Bill computation — pure, deterministic, no Django.

Given the active lines (each already net of line-level discounts) plus an
order-level discount and service-charge rate, produces the full breakup:

  subtotal -> (order discount, allocated proportionally per line)
           -> per-line GST via the catalog GST calculator (intra/inter-state)
           -> service charge on the post-discount taxable base
           -> round off to the nearest unit

Service charge is untaxed by default (the common Indian POS convention); tax is
computed per line so mixed GST rates in one bill are handled correctly.
"""
from dataclasses import dataclass
from decimal import Decimal

from contexts.catalog.domain.gst import compute_gst

from .finance import q, round_to_nearest


@dataclass(frozen=True)
class BillLine:
    amount: Decimal                       # line total before tax, after line discount
    tax_rate: Decimal                     # GST percent
    cess_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class BillBreakup:
    subtotal: Decimal
    discount: Decimal
    taxable: Decimal
    service_charge: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal
    tax_total: Decimal
    round_off: Decimal
    total: Decimal


def compute_bill(
    lines: list[BillLine],
    *,
    order_discount: Decimal = Decimal("0"),
    service_charge_rate: Decimal = Decimal("0"),
    interstate: bool = False,
    round_to: Decimal = Decimal("1"),
) -> BillBreakup:
    subtotal = q(sum((line.amount for line in lines), Decimal("0")))
    discount = q(min(Decimal(order_discount), subtotal)) if subtotal > 0 else Decimal("0.00")

    cgst = sgst = igst = cess = Decimal("0.00")
    allocated = Decimal("0.00")
    count = len(lines)

    for index, line in enumerate(lines):
        if subtotal > 0 and discount > 0:
            if index < count - 1:
                alloc = q(discount * line.amount / subtotal)
                allocated += alloc
            else:
                alloc = q(discount - allocated)  # last line absorbs rounding
        else:
            alloc = Decimal("0.00")

        taxable_line = line.amount - alloc
        breakup = compute_gst(
            taxable_line, line.tax_rate,
            interstate=interstate, cess_rate=line.cess_rate,
        )
        cgst += breakup.cgst
        sgst += breakup.sgst
        igst += breakup.igst
        cess += breakup.cess

    cgst, sgst, igst, cess = q(cgst), q(sgst), q(igst), q(cess)
    tax_total = q(cgst + sgst + igst + cess)

    taxable = q(subtotal - discount)
    service_charge = q(taxable * Decimal(service_charge_rate) / Decimal("100"))

    pre_round = q(taxable + service_charge + tax_total)
    total = round_to_nearest(pre_round, round_to)
    round_off = q(total - pre_round)

    return BillBreakup(
        subtotal=subtotal, discount=discount, taxable=taxable,
        service_charge=service_charge, cgst=cgst, sgst=sgst, igst=igst,
        cess=cess, tax_total=tax_total, round_off=round_off, total=total,
    )
