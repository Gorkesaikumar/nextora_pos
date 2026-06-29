"""Kitchen Order Tickets (KOT) — routed to kitchen stations."""
from django.db import models
from django.utils import timezone

from contexts.ordering.domain.enums import KOTStatus
from shared.tenancy.models import TenantAwareModel


class KOT(TenantAwareModel):
    order = models.ForeignKey(
        "ordering.Order", on_delete=models.CASCADE, related_name="kots"
    )
    location_id = models.UUIDField()
    kitchen_station_id = models.UUIDField(null=True, blank=True)
    number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=KOTStatus.choices, default=KOTStatus.NEW
    )
    printed_at = models.DateTimeField(null=True, blank=True)
    created_at_kot = models.DateTimeField(default=timezone.now)

    class Meta(TenantAwareModel.Meta):
        db_table = "kot"
        indexes = [
            models.Index(fields=["order"], name="ix_kot__order"),
        ]

    def __str__(self) -> str:
        return f"KOT#{self.number}"


class KOTItem(TenantAwareModel):
    kot = models.ForeignKey(KOT, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(
        "ordering.OrderItem", on_delete=models.CASCADE, related_name="kot_items"
    )
    name_snapshot = models.CharField(max_length=220)
    qty = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    notes = models.CharField(max_length=255, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "kot_item"
