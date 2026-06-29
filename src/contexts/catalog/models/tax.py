"""GST tax classes (tenant-scoped)."""
from django.db import models

from shared.tenancy.models import TenantAwareModel


class TaxInclusionType(models.TextChoices):
    INCLUSIVE = "INCLUSIVE", "Tax Inclusive (MRP)"
    EXCLUSIVE = "EXCLUSIVE", "Tax Exclusive (Added at checkout)"


class TaxClass(TenantAwareModel):
    name = models.CharField(max_length=80)          # e.g., "Food GST 5%"
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)  # percent
    cess_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Resolves SARB finding: Tax inclusion needs to be granular, not global
    inclusion_type = models.CharField(
        max_length=15,
        choices=TaxInclusionType.choices,
        default=TaxInclusionType.EXCLUSIVE,
        help_text="Whether base prices using this tax class include or exclude the tax amount."
    )
    
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "catalog_tax_class"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_tax_class__tenant_name",
            ),
            models.CheckConstraint(
                check=models.Q(gst_rate__gte=0) & models.Q(gst_rate__lte=100),
                name="ck_tax_class__gst_rate_range",
            ),
            models.CheckConstraint(
                check=models.Q(cess_rate__gte=0) & models.Q(cess_rate__lte=100),
                name="ck_tax_class__cess_rate_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.gst_rate}%)"
