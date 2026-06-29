"""Catalog domain events.

Events are immutable, past-tense facts published through the shared
transactional outbox (``shared.infrastructure.events``). They are written to the
``OutboxEvent`` table inside the *same* transaction as the business change, then
delivered to handlers asynchronously after commit — so a product write and its
event can never diverge.

Importing this package (done in ``CatalogConfig.ready``) registers the handlers.
"""
from .domain_events import (
    ProductCreated,
    ProductDeleted,
    ProductPriceChanged,
    ProductUpdated,
)
from .publisher import (
    publish_product_created,
    publish_product_deleted,
    publish_product_updated,
)

# Importing handlers registers them with the shared event registry.
from . import handlers  # noqa: F401  (side-effect import)

__all__ = [
    "ProductCreated",
    "ProductDeleted",
    "ProductPriceChanged",
    "ProductUpdated",
    "publish_product_created",
    "publish_product_deleted",
    "publish_product_updated",
]
