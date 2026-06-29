"""Concurrency-safe document-numbering counter (monthly period).

One row per (tenant, scope, period). Numbers are issued under a
``SELECT … FOR UPDATE`` lock so two concurrent receipts/transfers never produce
a duplicate document number. Because ``period`` (YYYYMM) is part of the key,
numbering resets automatically each month — mirroring ordering's DailyCounter.
"""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class DocumentSequence(TenantAwareModel):
    scope = models.CharField(
        max_length=30, help_text="purchase_order | transfer | adjustment"
    )
    period = models.CharField(max_length=6, help_text="YYYYMM bucket")
    last_number = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "inventory_document_sequence"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "scope", "period"],
                name="uq_doc_sequence__tenant_scope_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scope}:{self.period}:{self.last_number}"
