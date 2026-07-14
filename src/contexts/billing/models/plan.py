"""Subscription Plan catalog (global, database-driven).

Every plan grants 100% of Nextora POS features. The only difference between
plans is the subscription duration and price. No usage limits are enforced.
"""
from decimal import Decimal
from django.db import models

from contexts.billing.domain.enums import BillingInterval
from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class Plan(UUIDModel, TimeStampedModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    code = models.CharField(max_length=50, unique=True, help_text="URL-safe unique slug, e.g. 'monthly-pro'")
    name = models.CharField(max_length=100, help_text="Internal plan name")
    display_name = models.CharField(max_length=100, blank=True, help_text="Customer-facing name shown on pricing pages")
    description = models.TextField(blank=True, help_text="Short tagline shown on pricing cards")

    # ── Duration ──────────────────────────────────────────────────────────────
    duration_type = models.CharField(
        max_length=16,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
        help_text="Billing interval type (determines duration_days if not custom)",
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        help_text="Exact number of days this plan is valid after activation",
    )

    # ── Pricing ───────────────────────────────────────────────────────────────
    original_price = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
        help_text="Original/MRP price before discount",
    )
    sale_price = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
        help_text="Effective selling price charged to the customer",
    )
    currency = models.CharField(max_length=3, default="INR")
    gst_inclusive = models.BooleanField(
        default=True,
        help_text="If True, sale_price already includes GST. If False, GST is added on top.",
    )
    gst_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("18.00"),
        help_text="GST/tax percentage applied to this plan",
    )

    # ── Trial ─────────────────────────────────────────────────────────────────
    trial_eligible = models.BooleanField(default=True, help_text="Allow free trial for this plan")
    trial_days = models.PositiveIntegerField(default=0, help_text="Free trial duration in days (0 = no trial)")
    grace_days = models.PositiveIntegerField(default=7, help_text="Grace period after expiration before access is revoked")

    # ── Visibility & Status ───────────────────────────────────────────────────
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive plans are hidden everywhere and not selectable",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Visible to customers on Registration Wizard & Choose Plan pages",
    )

    # ── Display Flags & Badges ────────────────────────────────────────────────
    display_order = models.IntegerField(default=0, help_text="Lower = appears first on pricing page")
    is_featured = models.BooleanField(default=False, help_text="Show 'Featured' badge")
    is_recommended = models.BooleanField(default=False, help_text="Show 'Recommended' badge")
    is_popular = models.BooleanField(default=False, help_text="Show 'Popular' badge")
    is_default = models.BooleanField(default=False, help_text="Pre-selected on the registration wizard")

    # ── Feature Flags (future-proof) ──────────────────────────────────────────
    # NOTE: Core POS features are always 100% unlocked. This JSON is reserved
    # for future add-on flags that the Super Admin may optionally configure.
    features = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "plan"
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_duration_type_display()})"

    @property
    def effective_price(self) -> Decimal:
        """Return sale_price if set, otherwise original_price."""
        return self.sale_price if self.sale_price > 0 else self.original_price

    @property
    def has_discount(self) -> bool:
        return self.original_price > 0 and self.sale_price < self.original_price


class PlanPrice(UUIDModel, TimeStampedModel):
    """Optional per-interval price override. Used when a plan supports multiple
    billing cycles (e.g. a 'Pro' plan with monthly/yearly options)."""
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
