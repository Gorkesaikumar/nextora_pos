"""Subscription Visibility Configuration singleton model."""
from django.db import models
from shared.infrastructure.models.base import TimeStampedModel
from contexts.billing.domain.enums import BillingInterval


class SubscriptionVisibilityConfig(TimeStampedModel):
    """Singleton model for controlling which subscription billing durations are visible.

    If disabled:
    - It does not appear during registration.
    - It does not appear in the Choose Plan page or Upgrade screen.
    - Customers cannot purchase it.
    - Existing subscribers continue until expiry.
    """
    show_daily = models.BooleanField(default=False)
    show_weekly = models.BooleanField(default=False)
    show_monthly = models.BooleanField(default=True)
    show_quarterly = models.BooleanField(default=False)
    show_half_yearly = models.BooleanField(default=False)
    show_yearly = models.BooleanField(default=True)
    show_custom = models.BooleanField(default=False)

    class Meta:
        db_table = "subscription_visibility_config"
        verbose_name = "Subscription Visibility Configuration"
        verbose_name_plural = "Subscription Visibility Configuration"

    def __str__(self) -> str:
        return "Subscription Visibility Config"

    @classmethod
    def get_solo(cls) -> "SubscriptionVisibilityConfig":
        """Get or create the singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_visible_intervals(self) -> list[str]:
        """Return list of active intervals based on current toggles."""
        out = []
        if self.show_daily:
            out.append(BillingInterval.DAILY)
        if self.show_weekly:
            out.append(BillingInterval.WEEKLY)
        if self.show_monthly:
            out.append(BillingInterval.MONTHLY)
        if self.show_quarterly:
            out.append(BillingInterval.QUARTERLY)
        if self.show_half_yearly:
            out.append(BillingInterval.HALF_YEARLY)
        if self.show_yearly:
            out.append(BillingInterval.YEARLY)
        if self.show_custom:
            out.append(BillingInterval.CUSTOM)
        return out
