"""Global Trial Configuration singleton model."""
from django.db import models
from shared.infrastructure.models.base import TimeStampedModel


class GlobalTrialConfig(TimeStampedModel):
    """Singleton model for Super Admin trial management.

    Controls automatic free trials for new restaurant registrations.
    """
    is_enabled = models.BooleanField(
        default=True,
        help_text="Automatically grant a free trial on new restaurant registrations."
    )
    trial_days = models.PositiveIntegerField(
        default=14,
        help_text="Duration of the free trial in days (e.g. 7, 14, 30)."
    )
    grace_days = models.PositiveIntegerField(
        default=3,
        help_text="Grace period after trial expiration before blocking transaction operations."
    )
    banner_message = models.CharField(
        max_length=255,
        default="Free Trial — {days} Days Remaining. Upgrade before your trial expires.",
        help_text="Banner template. Use {days} for dynamic countdown."
    )
    expired_message = models.CharField(
        max_length=255,
        default="Your free trial has expired. Please choose a subscription plan to continue using Nextora POS.",
        help_text="Message shown when trial has expired and operations are locked."
    )
    reminder_days_before = models.PositiveIntegerField(
        default=3,
        help_text="Days before expiration to trigger reminder notifications."
    )

    class Meta:
        db_table = "global_trial_config"
        verbose_name = "Global Trial Configuration"
        verbose_name_plural = "Global Trial Configuration"

    def __str__(self) -> str:
        return f"Trial Config ({self.trial_days} days, enabled={self.is_enabled})"

    @classmethod
    def get_solo(cls) -> "GlobalTrialConfig":
        """Get or create the singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
