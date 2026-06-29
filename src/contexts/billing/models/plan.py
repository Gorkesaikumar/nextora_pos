"""Plan catalog (global). Limits use NULL = unlimited.

A Plan groups limits + features; a PlanPrice holds the amount for each billing
interval, so one plan offers monthly/quarterly/yearly pricing.
"""
from django.db import models

from contexts.billing.domain.enums import BillingInterval
from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class Plan(UUIDModel, TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)   # "starter", "pro"
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)         # shown on pricing page

    trial_days = models.PositiveIntegerField(default=0)
    grace_days = models.PositiveIntegerField(default=7)

    # Limits — NULL means unlimited.
    max_branches = models.PositiveIntegerField(null=True, blank=True)
    max_employees = models.PositiveIntegerField(null=True, blank=True)
    max_invoices_per_month = models.PositiveIntegerField(null=True, blank=True)
    max_storage_mb = models.PositiveIntegerField(null=True, blank=True)

    # Boolean / valued feature flags, e.g. {"kds": true, "api_access": true}.
    features = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "plan"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.code


class PlanPrice(UUIDModel, TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    interval = models.CharField(max_length=16, choices=BillingInterval.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    class Meta:
        db_table = "plan_price"
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "interval", "currency"],
                name="uq_plan_price__plan_interval_currency",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gte=0), name="ck_plan_price__amount_nonneg"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan.code} {self.interval} {self.amount}{self.currency}"
