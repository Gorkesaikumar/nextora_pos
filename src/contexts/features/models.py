from django.db import models
from shared.infrastructure.models.base import BaseModel


class RuleType(models.TextChoices):
    TENANT = "tenant", "Tenant Specific"
    SUBSCRIPTION = "subscription", "Subscription Tier"
    COUNTRY = "country", "Country"
    PERCENTAGE = "percentage", "Percentage Rollout"
    AB_TEST = "ab_test", "A/B Test Bucket"


class FeatureFlag(BaseModel):
    key = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_state = models.BooleanField(default=False)
    is_kill_switch = models.BooleanField(
        default=False, 
        help_text="If true, evaluates to False ignoring all rules."
    )

    def __str__(self):
        return self.key


class FeatureRule(BaseModel):
    flag = models.ForeignKey(FeatureFlag, on_delete=models.CASCADE, related_name="rules")
    priority = models.PositiveIntegerField(default=0, db_index=True)
    rule_type = models.CharField(max_length=50, choices=RuleType.choices)
    target_value = models.JSONField(
        help_text="Expected format: list of strings for TENANT/SUBSCRIPTION/COUNTRY, integer (0-100) for PERCENTAGE, or list of bucket strings for AB_TEST"
    )
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.flag.key} - {self.get_rule_type_display()}"
