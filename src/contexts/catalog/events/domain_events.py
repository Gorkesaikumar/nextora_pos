"""Catalog domain event definitions.

Each event extends the shared :class:`DomainEvent` (which supplies ``event_id``,
``occurred_at``, ``tenant_id`` and ``event_version`` — all defaulted). Because
the base fields carry defaults, every subclass field must also default;
publishers always pass them explicitly. Payloads stay JSON-safe (UUIDs are
serialised by the dispatcher; money is carried as a string) so the outbox can
store them without a custom encoder.
"""
import uuid
from dataclasses import dataclass, field

from shared.domain.events import DomainEvent


@dataclass(frozen=True)
class ProductCreated(DomainEvent):
    product_id: uuid.UUID | None = None
    sku: str = ""
    name: str = ""
    category_id: uuid.UUID | None = None
    base_price: str = "0"
    currency: str = ""


@dataclass(frozen=True)
class ProductUpdated(DomainEvent):
    product_id: uuid.UUID | None = None
    sku: str = ""
    #: ``{field: {"from": old, "to": new}}`` — only the fields that changed.
    changed_fields: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProductPriceChanged(DomainEvent):
    product_id: uuid.UUID | None = None
    sku: str = ""
    old_price: str = "0"
    new_price: str = "0"
    currency: str = ""


@dataclass(frozen=True)
class ProductDeleted(DomainEvent):
    product_id: uuid.UUID | None = None
    sku: str = ""
