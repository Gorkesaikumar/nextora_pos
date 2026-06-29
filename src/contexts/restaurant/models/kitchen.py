"""Kitchen stations and printers — hardware topology of a branch."""
from django.db import models

from contexts.restaurant.domain.enums import PrinterKind, StationKind
from shared.tenancy.models import TenantAwareModel


class KitchenStation(TenantAwareModel):
    """A preparation station in the kitchen (e.g., Grill, Bar, Tandoor).

    Orders are routed to stations based on product → category → station mapping
    in the catalog context.
    """
    branch = models.ForeignKey(
        "restaurant.Branch", on_delete=models.CASCADE, related_name="kitchen_stations"
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=15, choices=StationKind.choices, default=StationKind.OTHER
    )
    # Display order on KDS (Kitchen Display System)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_station"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_r_station__branch_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["branch", "is_active"],
                name="ix_r_station__branch_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Printer(TenantAwareModel):
    """A physical printer at a branch (receipt, KOT, label)."""
    branch = models.ForeignKey(
        "restaurant.Branch", on_delete=models.CASCADE, related_name="printers"
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=12, choices=PrinterKind.choices, default=PrinterKind.RECEIPT
    )
    # Connection details (value object stored as structured JSON)
    connection = models.JSONField(
        default=dict, blank=True,
        help_text="Connection config: {protocol, ip_address, port, driver}"
    )
    # Link to a kitchen station for KOT routing
    station = models.ForeignKey(
        KitchenStation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="printers",
        help_text="Station this KOT printer serves (null for receipt/label printers)"
    )
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_printer"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_r_printer__branch_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["branch", "kind"],
                condition=models.Q(is_active=True),
                name="ix_r_printer__branch_kind",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.kind})"
