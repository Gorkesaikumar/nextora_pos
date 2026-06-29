"""Concurrency-safe document numbering for inventory documents.

Replaces the previous ``max(number)+1`` scan, which raced under concurrency and
could mint duplicate numbers. Numbering is monthly (``PREFIX-YYYYMM-NNNN``) and
issued under a ``SELECT … FOR UPDATE`` row lock on a per-(tenant, scope, period)
counter — mirroring ordering's ``sequences.next_number``.
"""
from datetime import date

from django.db import transaction
from django.utils import timezone

from contexts.inventory.models import DocumentSequence

# Document scopes (also the DocumentSequence.scope value).
SCOPE_PURCHASE_ORDER = "purchase_order"
SCOPE_TRANSFER = "transfer"
SCOPE_ADJUSTMENT = "adjustment"


def next_document_number(scope: str, prefix: str, *, on: date | None = None) -> str:
    """Return the next ``PREFIX-YYYYMM-NNNN`` number for ``scope``.

    Must run with a tenant bound in context (the counter is tenant-scoped). The
    lock serialises concurrent callers so numbers are gapless and unique.
    """
    on = on or timezone.localdate()
    period = f"{on.year}{on.month:02d}"

    with transaction.atomic():
        seq, _ = DocumentSequence.objects.get_or_create(scope=scope, period=period)
        seq = DocumentSequence.objects.select_for_update().get(pk=seq.pk)
        seq.last_number += 1
        seq.save(update_fields=["last_number", "updated_at"])

    return f"{prefix}-{period}-{seq.last_number:04d}"
