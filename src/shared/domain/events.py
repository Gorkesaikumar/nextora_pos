"""Domain event base.

Events are immutable facts named in the past tense (OrderPlaced, InvoiceIssued).
They carry a UUID, an occurrence timestamp, and the tenant they belong to so
they can be routed, audited, and projected without ambiguity.
"""
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: uuid.UUID | None = None
    event_version: int = 1

    @property
    def name(self) -> str:
        """Stable event name used as the outbox/topic key."""
        return type(self).__name__
