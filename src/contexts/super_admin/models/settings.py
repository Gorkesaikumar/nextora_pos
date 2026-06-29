from django.db import models
from django.utils.translation import gettext_lazy as _


class PlatformSettings(models.Model):
    """
    Singleton model for global SaaS configuration.
    """
    maintenance_mode = models.BooleanField(default=False, help_text="If true, disables tenant access temporarily.")
    global_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    base_currency = models.CharField(max_length=3, default="USD")

    # Branding
    platform_name = models.CharField(max_length=100, default="Nextora POS")
    support_email = models.EmailField(default="support@nextorapos.com")
    
    # Legal
    terms_url = models.URLField(blank=True)
    privacy_url = models.URLField(blank=True)

    class Meta:
        db_table = "platform_settings"
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Platform Settings ({self.platform_name})"
