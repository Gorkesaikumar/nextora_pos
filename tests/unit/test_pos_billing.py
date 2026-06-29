"""Pure bill-computation tests (no DB)."""
from decimal import Decimal

from contexts.ordering.domain.billing import BillLine, compute_bill
from contexts.ordering.domain.finance import financial_year, round_to_nearest
from datetime import date


def test_simple_intrastate_gst():
    b = compute_bill([BillLine(Decimal("100"), Decimal("18"))])
    assert b.subtotal == Decimal("100.00")
    assert b.cgst == Decimal("9.00")
    assert b.sgst == Decimal("9.00")
    assert b.igst == Decimal("0.00")
    assert b.tax_total == Decimal("18.00")
    assert b.total == Decimal("118.00")


def test_interstate_gst():
    b = compute_bill([BillLine(Decimal("100"), Decimal("18"))], interstate=True)
    assert b.igst == Decimal("18.00")
    assert b.total == Decimal("118.00")


def test_discount_service_charge_and_round_off():
    # 100 - 10 discount = 90 taxable; SC 10% = 9; GST 18% on 90 = 16.20
    # pre-round = 90 + 9 + 16.20 = 115.20 -> rounds to 115, round_off -0.20
    b = compute_bill(
        [BillLine(Decimal("100"), Decimal("18"))],
        order_discount=Decimal("10"),
        service_charge_rate=Decimal("10"),
    )
    assert b.taxable == Decimal("90.00")
    assert b.service_charge == Decimal("9.00")
    assert b.tax_total == Decimal("16.20")
    assert b.total == Decimal("115.00")
    assert b.round_off == Decimal("-0.20")


def test_mixed_tax_rates():
    b = compute_bill([
        BillLine(Decimal("100"), Decimal("5")),
        BillLine(Decimal("100"), Decimal("18")),
    ])
    assert b.subtotal == Decimal("200.00")
    assert b.tax_total == Decimal("23.00")   # 5 + 18
    assert b.total == Decimal("223.00")


def test_round_to_nearest():
    assert round_to_nearest(Decimal("115.20"), Decimal("1")) == Decimal("115.00")
    assert round_to_nearest(Decimal("115.60"), Decimal("1")) == Decimal("116.00")


def test_financial_year():
    assert financial_year(date(2026, 6, 27)) == "2026-2027"
    assert financial_year(date(2026, 2, 1)) == "2025-2026"
