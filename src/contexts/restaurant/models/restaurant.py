"""Restaurant — the Aggregate Root (Brand/Concept).

A Restaurant represents a distinct Brand or Concept owned by a Tenant.
A tenant may own multiple concepts (e.g., "Nextora Burger", "Nextora Cafe").
Each Restaurant can have multiple physical Branch locations.
"""
import uuid
from django.db import models

from contexts.restaurant.domain.enums import RestaurantStatus
from shared.tenancy.models import TenantAwareModel


class Restaurant(TenantAwareModel):
    name = models.CharField(max_length=200, help_text="The Brand/Concept name")
    slug = models.SlugField(max_length=80, help_text="URL-safe identifier")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=RestaurantStatus.choices,
        default=RestaurantStatus.DRAFT,
    )
    logo = models.ImageField(
        upload_to="restaurant/logos/", null=True, blank=True
    )
    
    # Brand-level default address (headquarters)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=2, default="IN", help_text="ISO 3166-1 alpha-2")

    is_default = models.BooleanField(
        default=False,
        help_text="Auto-created default restaurant concept for single-brand tenants"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant"
        ordering = ["name"]
        constraints = [
            # A brand name must be unique per tenant
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_restaurant__tenant_name",
            ),
            models.UniqueConstraint(
                fields=["tenant", "slug"],
                condition=models.Q(is_deleted=False),
                name="uq_restaurant__tenant_slug",
            ),
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_default=True, is_deleted=False),
                name="uq_restaurant__one_default",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "status"],
                condition=models.Q(is_deleted=False),
                name="ix_restaurant__tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.name
