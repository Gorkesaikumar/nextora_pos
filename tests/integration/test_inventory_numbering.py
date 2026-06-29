"""Concurrency-safe document numbering tests."""
import re
from datetime import date

import pytest

from contexts.inventory.models import DocumentSequence
from contexts.inventory.services import numbering

pytestmark = pytest.mark.django_db


def test_number_format(active_tenant):
    number = numbering.next_document_number(
        numbering.SCOPE_PURCHASE_ORDER, "PO", on=date(2026, 6, 1)
    )
    assert re.fullmatch(r"PO-202606-0001", number)


def test_numbers_are_sequential_within_period(active_tenant):
    n1 = numbering.next_document_number(numbering.SCOPE_TRANSFER, "TRF", on=date(2026, 6, 1))
    n2 = numbering.next_document_number(numbering.SCOPE_TRANSFER, "TRF", on=date(2026, 6, 2))
    assert n1.endswith("-0001")
    assert n2.endswith("-0002")  # same YYYYMM period


def test_period_resets_each_month(active_tenant):
    a = numbering.next_document_number(numbering.SCOPE_ADJUSTMENT, "ADJ", on=date(2026, 6, 9))
    b = numbering.next_document_number(numbering.SCOPE_ADJUSTMENT, "ADJ", on=date(2026, 7, 9))
    assert a == "ADJ-202606-0001"
    assert b == "ADJ-202607-0001"


def test_scopes_are_independent(active_tenant):
    po = numbering.next_document_number(numbering.SCOPE_PURCHASE_ORDER, "PO", on=date(2026, 6, 1))
    trf = numbering.next_document_number(numbering.SCOPE_TRANSFER, "TRF", on=date(2026, 6, 1))
    assert po.endswith("-0001")
    assert trf.endswith("-0001")
    assert DocumentSequence.objects.count() == 2
