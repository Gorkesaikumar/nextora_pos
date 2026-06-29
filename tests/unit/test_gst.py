"""GST computation tests (pure, no DB)."""
from decimal import Decimal

from contexts.catalog.domain.gst import compute_gst


def test_intrastate_exclusive_splits_cgst_sgst():
    r = compute_gst(Decimal("100"), Decimal("18"), interstate=False)
    assert r.taxable == Decimal("100.00")
    assert r.cgst == Decimal("9.00")
    assert r.sgst == Decimal("9.00")
    assert r.igst == Decimal("0.00")
    assert r.total_tax == Decimal("18.00")
    assert r.total == Decimal("118.00")


def test_interstate_uses_igst():
    r = compute_gst(Decimal("100"), Decimal("18"), interstate=True)
    assert r.igst == Decimal("18.00")
    assert r.cgst == Decimal("0.00")
    assert r.total == Decimal("118.00")


def test_inclusive_pricing_back_calculates_taxable():
    r = compute_gst(Decimal("118"), Decimal("18"), interstate=False, inclusive=True)
    assert r.taxable == Decimal("100.00")
    assert r.total == Decimal("118.00")


def test_cess_is_added():
    r = compute_gst(
        Decimal("100"), Decimal("18"), interstate=True, cess_rate=Decimal("12")
    )
    assert r.cess == Decimal("12.00")
    assert r.total_tax == Decimal("30.00")
    assert r.total == Decimal("130.00")
