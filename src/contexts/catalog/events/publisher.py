"""Publish catalog events through the shared transactional outbox.

These helpers stamp the active tenant onto each event and hand it to
``shared.infrastructure.events.dispatcher.dispatch``, which persists it to the
outbox within the current transaction and schedules delivery on commit. Call
them *inside* the service transaction that made the change.
"""
import uuid

from shared.domain.events import DomainEvent
from shared.infrastructure.events.dispatcher import dispatch
from shared.tenancy.context import get_current_tenant

from contexts.catalog.models import Product

from .domain_events import (
    ProductCreated,
    ProductDeleted,
    ProductPriceChanged,
    ProductUpdated,
)


def _publish(event: DomainEvent) -> None:
    dispatch(event)


def publish_product_created(product: Product) -> None:
    _publish(
        ProductCreated(
            tenant_id=get_current_tenant(),
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            category_id=product.category_id,
            base_price=str(product.base_price),
            currency=product.currency,
        )
    )


def publish_product_updated(product: Product, changed_fields: dict) -> None:
    tenant_id = get_current_tenant()
    _publish(
        ProductUpdated(
            tenant_id=tenant_id,
            product_id=product.id,
            sku=product.sku,
            changed_fields=changed_fields,
        )
    )
    # A price change is significant enough to warrant its own event so
    # downstream consumers (menu cache, pricing analytics) can subscribe to it
    # without parsing the generic update diff.
    price_change = changed_fields.get("base_price")
    if price_change:
        _publish(
            ProductPriceChanged(
                tenant_id=tenant_id,
                product_id=product.id,
                sku=product.sku,
                old_price=str(price_change.get("from")),
                new_price=str(price_change.get("to")),
                currency=product.currency,
            )
        )


def publish_product_deleted(product_id: uuid.UUID, sku: str) -> None:
    _publish(
        ProductDeleted(
            tenant_id=get_current_tenant(),
            product_id=product_id,
            sku=sku,
        )
    )
