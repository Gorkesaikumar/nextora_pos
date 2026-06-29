"""DiningTable — the physical dining layout."""
from django.db import models

from contexts.restaurant.domain.enums import TableShape, TableStatus
from shared.tenancy.models import TenantAwareModel


class DiningTable(TenantAwareModel):
    """A single dining table in a branch.

    Supports status-machine transitions, table merging, and floor-plan shape.
    """
    branch = models.ForeignKey(
        "restaurant.Branch", on_delete=models.CASCADE, related_name="tables",
        null=True, blank=True
    )
    number = models.CharField(max_length=20, help_text="Table identifier, e.g., T1, A3")
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(
        max_length=15,
        choices=TableStatus.choices,
        default=TableStatus.VACANT,
    )
    assigned_waiter_id = models.UUIDField(null=True, blank=True)
    shape = models.CharField(
        max_length=15,
        choices=TableShape.choices,
        default=TableShape.SQUARE,
    )

    # Table merging: merged tables point to the "primary" table.
    merge_group = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="merged_tables",
        help_text="Primary table in a merge group"
    )

    # Floor-plan positioning (for visual layout rendering)
    position_x = models.PositiveIntegerField(default=0, help_text="X coordinate on floor plan")
    position_y = models.PositiveIntegerField(default=0, help_text="Y coordinate on floor plan")
    rotation = models.PositiveIntegerField(default=0, help_text="Rotation angle 0-359")

    # QR code for customer self-ordering
    qr_code_url = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_table"
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "number"],
                condition=models.Q(is_deleted=False),
                name="uq_r_table__branch_number",
            ),
            models.CheckConstraint(
                check=models.Q(capacity__gte=1),
                name="ck_r_table__capacity_gte_1",
            ),
            models.CheckConstraint(
                check=models.Q(rotation__gte=0) & models.Q(rotation__lt=360),
                name="ck_r_table__rotation_range",
            ),
        ]
        indexes = [
            # Branch-wide table dashboard
            models.Index(
                fields=["tenant", "status"],
                condition=models.Q(is_deleted=False),
                name="ix_r_table__tenant_status",
            ),
        ]

    def __str__(self) -> str:
        if self.branch:
            return f"Table {self.number} ({self.branch.code})"
        return f"Table {self.number}"
