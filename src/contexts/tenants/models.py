"""Tenant aggregate — the root of multi-tenancy.

These tables are GLOBAL: they have no tenant_id and are not RLS-scoped, because
they define the tenants themselves. They use UUIDv4 PKs (low volume) and are
read on the request hot path (cached by the resolver).
"""
from django.db import models

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel
from shared.tenancy.models import TenantAwareModel

class TenantCategory(models.TextChoices):
    RESTAURANT = "restaurant", "Restaurant"
    CAFE = "cafe", "Cafe"
    BAKERY = "bakery", "Bakery"
    HOTEL = "hotel", "Hotel"
    CLOUD_KITCHEN = "cloud_kitchen", "Cloud Kitchen"

class Tenant(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        TRIAL = "trial"
        ACTIVE = "active"
        SUSPENDED = "suspended"
        CHURNED = "churned"

    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(
        max_length=50, choices=TenantCategory.choices, default=TenantCategory.RESTAURANT
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.TRIAL, db_index=True
    )
    country = models.CharField(max_length=2, blank=True)       # ISO-3166
    base_currency = models.CharField(max_length=3, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")

    class Meta:
        db_table = "tenant"
        constraints = [
            models.CheckConstraint(
                name="ck_tenant__currency_format",
                check=models.Q(base_currency__regex=r"^[A-Z]{3}$"),
            ),
        ]
        indexes = [
            # Ops list of live tenants; excludes the growing churned set.
            models.Index(
                fields=["status"],
                name="ix_tenant__status_live",
                condition=~models.Q(status="churned"),
            ),
        ]

    def __str__(self) -> str:
        return self.slug

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.TRIAL, self.Status.ACTIVE}


class TenantDomain(UUIDModel, TimeStampedModel):
    """Custom domains / white-label hostnames mapping to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="domains"
    )
    domain = models.CharField(max_length=253, unique=True)  # a host -> one tenant
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "tenant_domain"
        constraints = [
            # At most one primary domain per tenant (partial unique).
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_primary=True),
                name="uq_tenant_domain__one_primary",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"], name="ix_tenant_domain__tenant"),
        ]

    def __str__(self) -> str:
        return self.domain

    def save(self, *args, **kwargs):  # normalize host for stable lookups
        self.domain = self.domain.lower().strip()
        super().save(*args, **kwargs)


class TenantConfiguration(TenantAwareModel):
    gst_number = models.CharField(max_length=15, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    invoice_prefix = models.CharField(max_length=10, default="INV")
    invoice_footer = models.TextField(blank=True)
    
    printer_settings = models.JSONField(default=dict, blank=True)
    kitchen_settings = models.JSONField(default=dict, blank=True)
    discount_rules = models.JSONField(default=dict, blank=True)
    tax_rules = models.JSONField(default=dict, blank=True)
    notification_settings = models.JSONField(default=dict, blank=True)
    business_hours = models.JSONField(default=dict, blank=True)
    working_days = models.JSONField(default=list, blank=True)
    theme = models.JSONField(default=dict, blank=True)
    logo = models.ImageField(upload_to="tenant_logos/", null=True, blank=True)
    language = models.CharField(max_length=10, default="en")

    class Meta(TenantAwareModel.Meta):
        db_table = "tenant_configuration"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="uq_tenant_configuration__tenant"
            )
        ]

    def __str__(self) -> str:
        return f"Config for {self.tenant_id}"


class TableStatus(models.TextChoices):
    VACANT = "vacant", "Vacant"
    OCCUPIED = "occupied", "Occupied"
    RESERVED = "reserved", "Reserved"


class Table(TenantAwareModel):
    number = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.VACANT
    )
    qr_code_url = models.CharField(max_length=500, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "tenant_table"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="uq_table__tenant_number"
            )
        ]
        ordering = ["number"]

    def __str__(self) -> str:
        return f"Table {self.number}"


class CashCounter(TenantAwareModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "tenant_cash_counter"

    def __str__(self) -> str:
        return self.name


class Holiday(TenantAwareModel):
    date = models.DateField()
    name = models.CharField(max_length=255)

    class Meta(TenantAwareModel.Meta):
        db_table = "tenant_holiday"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "date"],
                name="uq_holiday__tenant_date"
            )
        ]
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"
