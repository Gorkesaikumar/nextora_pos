"""Operational infrastructure — CashCounter, BusinessHours, Holiday, GST, Settings."""
import re

from django.core.exceptions import ValidationError
from django.db import models

from contexts.restaurant.domain.enums import DayOfWeek, GSTRegistrationType
from shared.tenancy.models import TenantAwareModel

# Regex per GSTIN format: 2-digit state code + PAN + entity code + Z + checksum
GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")


class CashCounter(TenantAwareModel):
    """A physical cash register / POS terminal."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_counter"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                condition=models.Q(is_deleted=False),
                name="uq_r_counter__tenant_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class BusinessHours(TenantAwareModel):
    """Structured per-day operating hours.

    One row per day of the week (max 7 per tenant). Validated: open < close.
    """
    day_of_week = models.PositiveSmallIntegerField(
        choices=DayOfWeek.choices,
        help_text="ISO 8601 day: 1=Monday … 7=Sunday"
    )
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(
        default=False,
        help_text="If true, closed on this day (open/close times ignored)"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_hours"
        ordering = ["day_of_week"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "day_of_week"],
                condition=models.Q(is_deleted=False),
                name="uq_r_hours__tenant_day",
            ),
        ]

    def clean(self):
        if not self.is_closed and self.open_time and self.close_time:
            if self.open_time >= self.close_time:
                raise ValidationError(
                    "Opening time must be before closing time."
                )

    def __str__(self) -> str:
        if self.is_closed:
            return f"{self.get_day_of_week_display()} — CLOSED"
        return f"{self.get_day_of_week_display()} {self.open_time}–{self.close_time}"


class Holiday(TenantAwareModel):
    """A holiday / closure date."""
    date = models.DateField()
    name = models.CharField(max_length=200)
    is_full_day = models.BooleanField(default=True)
    open_time = models.TimeField(
        null=True, blank=True,
        help_text="If not full-day, modified opening time"
    )
    close_time = models.TimeField(
        null=True, blank=True,
        help_text="If not full-day, modified closing time"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_holiday"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "date"],
                condition=models.Q(is_deleted=False),
                name="uq_r_holiday__tenant_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"


class RestaurantGSTProfile(TenantAwareModel):
    """Per-restaurant GST registration (mandatory for Indian operations)."""
    restaurant = models.OneToOneField(
        "restaurant.Restaurant", on_delete=models.CASCADE, related_name="gst_profile"
    )
    gstin = models.CharField(
        max_length=15,
        help_text="15-character GSTIN"
    )
    legal_name = models.CharField(max_length=255, help_text="Legal name on GST certificate")
    state_code = models.CharField(max_length=2, help_text="2-digit state code from GSTIN")
    registration_type = models.CharField(
        max_length=20,
        choices=GSTRegistrationType.choices,
        default=GSTRegistrationType.REGULAR,
    )
    pan = models.CharField(max_length=10, blank=True, help_text="PAN extracted from GSTIN")
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_gst_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant"],
                condition=models.Q(is_deleted=False),
                name="uq_r_gst__restaurant",
            ),
        ]

    def clean(self):
        if self.gstin and not GSTIN_PATTERN.match(self.gstin):
            raise ValidationError(
                f"Invalid GSTIN format: {self.gstin}. "
                "Expected: 2-digit state code + 5 alpha + 4 digits + alpha + digit + Z + alphanumeric."
            )
        if self.gstin:
            self.state_code = self.gstin[:2]
            self.pan = self.gstin[2:12]

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.gstin} ({self.legal_name})"


class RestaurantSettings(TenantAwareModel):
    """Per-restaurant configuration settings.

    Non-GST settings: invoice formatting, order flow
    preferences, display options, etc.
    """
    restaurant = models.OneToOneField(
        "restaurant.Restaurant", on_delete=models.CASCADE, related_name="settings"
    )
    # Invoice / billing
    invoice_prefix = models.CharField(max_length=10, default="INV")
    invoice_footer = models.TextField(blank=True)

    # Ordering behavior
    auto_accept_orders = models.BooleanField(
        default=False, help_text="Automatically accept incoming orders"
    )
    default_order_type = models.CharField(
        max_length=20, default="dine_in",
        help_text="Default order type when not specified"
    )
    enable_customer_self_ordering = models.BooleanField(
        default=False, help_text="Allow QR-based self-ordering"
    )

    # Display
    table_layout_mode = models.CharField(
        max_length=20, default="grid",
        help_text="Floor plan display mode: grid, freeform"
    )

    # Notification
    notification_settings = models.JSONField(default=dict, blank=True)

    # Theme overrides
    theme = models.JSONField(default=dict, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "restaurant_settings"
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant"],
                condition=models.Q(is_deleted=False),
                name="uq_r_settings__restaurant",
            ),
        ]

    def __str__(self) -> str:
        return f"Settings for {self.restaurant.name}"
