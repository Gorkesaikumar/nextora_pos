"""Category tree (tenant-scoped). A sub-category is a category with a parent."""
import uuid
from django.db import models

from shared.tenancy.models import TenantAwareModel


class Category(TenantAwareModel):
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, help_text="URL-safe identifier")
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)

    # Cross-context routing inherited by products in this category.
    # Points to restaurant.KitchenStation and restaurant.Printer
    station_id = models.UUIDField(
        null=True, blank=True, 
        help_text="UUID of the default kitchen station for routing."
    )
    printer_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID of the default KOT printer for routing."
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "catalog_category"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "parent", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_category__tenant_parent_name",
            ),
            models.UniqueConstraint(
                fields=["tenant", "slug"],
                condition=models.Q(is_deleted=False),
                name="uq_category__tenant_slug",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "parent"], name="ix_category__tenant_parent"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_root(self) -> bool:
        return self.parent_id is None
