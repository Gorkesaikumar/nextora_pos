"""Data access for purchase orders and their lines."""
import uuid

from django.db import models

from contexts.inventory.domain.enums import PurchaseOrderStatus
from contexts.inventory.models import PurchaseOrder, PurchaseOrderLine

from .base import BaseRepository


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    model = PurchaseOrder

    def with_lines(self) -> models.QuerySet[PurchaseOrder]:
        return self.get_queryset().select_related("supplier", "warehouse").prefetch_related("lines")

    def lock(self, entity_id: uuid.UUID) -> PurchaseOrder | None:
        # Lock the PO header for receipt processing (status transition).
        return self.get_queryset().select_for_update().filter(pk=entity_id).first()

    def open_orders(self) -> models.QuerySet[PurchaseOrder]:
        return self.get_queryset().filter(
            status__in=[
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
            ]
        )

    def number_exists(self, order_number: str) -> bool:
        return self.get_queryset().filter(order_number=order_number).exists()


class PurchaseOrderLineRepository(BaseRepository[PurchaseOrderLine]):
    model = PurchaseOrderLine

    def for_order(self, order_id: uuid.UUID) -> models.QuerySet[PurchaseOrderLine]:
        return self.get_queryset().filter(purchase_order_id=order_id).select_related(
            "inventory_item"
        )
