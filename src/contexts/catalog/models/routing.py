"""Printer and kitchen-station routing targets (tenant-scoped, branch-aware)."""
from django.db import models

from contexts.catalog.domain.enums import PrinterKind
from shared.tenancy.models import TenantAwareModel


class Printer(TenantAwareModel):
    # location_id is a soft reference to a branch (tenants.Location, added later).
    location_id = models.UUIDField(null=True, blank=True)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=12, choices=PrinterKind.choices, default=PrinterKind.RECEIPT
    )
    connection = models.JSONField(default=dict, blank=True)  # ip/port/driver
    is_active = models.BooleanField(default=True)
    brand = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    connection_type = models.CharField(
        max_length=20,
        choices=[('usb', 'USB'), ('lan', 'LAN'), ('wifi', 'Wi-Fi'), ('bluetooth', 'Bluetooth')],
        default='lan'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.IntegerField(default=9100)
    paper_width = models.CharField(
        max_length=10,
        choices=[('80mm', '80mm'), ('58mm', '58mm'), ('a4', 'A4')],
        default='80mm'
    )
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='online')

    class Meta(TenantAwareModel.Meta):
        db_table = "printer"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_printer__tenant_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.kind})"


class KitchenStation(TenantAwareModel):
    location_id = models.UUIDField(null=True, blank=True)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)        # "Grill", "Bar", "Tandoor"
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "kitchen_station"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_kitchen_station__tenant_code",
            ),
        ]

    def __str__(self) -> str:
        return self.name
