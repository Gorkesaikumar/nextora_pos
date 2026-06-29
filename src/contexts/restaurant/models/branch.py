"""Branch — the operational unit of a Restaurant Brand.

A Branch is a single physical establishment.
"""

from django.db import models

from contexts.restaurant.domain.enums import BranchStatus, ServiceMode
from shared.tenancy.models import TenantAwareModel


class Branch(TenantAwareModel):
    restaurant = models.ForeignKey(
        "restaurant.Restaurant",
        on_delete=models.PROTECT,
        related_name="branches",
        help_text="The Brand/Concept this branch belongs to."
    )
    name = models.CharField(max_length=200, help_text="e.g., Downtown, Mall of India")
    code = models.CharField(max_length=30, help_text="Short unique code, e.g., MUM-01")
    status = models.CharField(
        max_length=25,
        choices=BranchStatus.choices,
        default=BranchStatus.SETUP,
    )

    # Address (value object stored inline)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=2, default="IN")

    # Geo-location
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Service modes this branch supports (stored as a list of strings in JSON)
    service_modes = models.JSONField(
        default=list,
        blank=True,
    )

    # Operational
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    currency = models.CharField(max_length=3, default="INR")
    is_active = models.BooleanField(default=True)
    manager_id = models.UUIDField(null=True, blank=True)
    logo = models.ImageField(upload_to="branch_logos/", null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_branch"
        ordering = ["name"]
        constraints = [
            # A branch code is unique per brand (restaurant)
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_r_branch__restaurant_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["restaurant", "status"],
                condition=models.Q(is_deleted=False),
                name="ix_r_branch__rest_status",
            ),
            models.Index(
                fields=["tenant", "is_active"],
                name="ix_r_branch__tenant_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
