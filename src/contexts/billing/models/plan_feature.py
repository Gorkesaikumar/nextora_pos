from django.db import models
from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class PlanFeature(UUIDModel, TimeStampedModel):
    plan = models.ForeignKey("billing.Plan", on_delete=models.CASCADE, related_name="plan_features")
    name = models.CharField(max_length=255, help_text="e.g. 'Up to 3 branches'")
    is_included = models.BooleanField(default=True, help_text="If False, the feature will appear crossed out")
    display_order = models.IntegerField(default=0, help_text="Lower = appears first on the list")

    class Meta:
        db_table = "plan_feature"
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return f"{self.plan.code} - {self.name}"
