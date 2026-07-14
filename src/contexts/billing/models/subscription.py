"""Subscription aggregate (tenant-scoped)."""
from django.db import models
from django.utils import timezone

from contexts.billing.domain.enums import (
    BillingInterval,
    SubscriptionStatus,
)
from shared.tenancy.models import TenantAwareModel


class Subscription(TenantAwareModel):
    plan = models.ForeignKey(
        "billing.Plan", on_delete=models.PROTECT, related_name="subscriptions"
    )
    interval = models.CharField(max_length=16, choices=BillingInterval.choices)
    price_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIALING,
        db_index=True,
    )
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField(db_index=True)
    grace_until = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    # Gateway linkage (Razorpay subscription id, etc.).
    provider = models.CharField(max_length=30, blank=True)
    provider_subscription_id = models.CharField(max_length=120, blank=True)

    renewal_count = models.PositiveIntegerField(default=0)
    applied_coupon_code = models.CharField(max_length=50, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "subscription"
        constraints = [
            # At most one live subscription per tenant.
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(
                    status__in=SubscriptionStatus.occupied(), is_deleted=False
                ),
                name="uq_subscription__one_live_per_tenant",
            ),
            models.CheckConstraint(
                check=models.Q(current_period_end__gt=models.F("current_period_start")),
                name="ck_subscription__period_order",
            ),
        ]
        indexes = [
            # Beat job scans live subscriptions whose period is ending.
            models.Index(
                fields=["current_period_end"],
                name="ix_sub__period_end_live",
                condition=models.Q(
                    status__in=SubscriptionStatus.occupied(), is_deleted=False
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.plan_id}:{self.status}"

    # --- Access & License predicates --------------------------------------
    def has_access(self, *, now=None) -> bool:
        """Whether the tenant should currently be served."""
        now = now or timezone.now()
        if self.status in (SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE):
            return self.current_period_end > now or self.in_grace
        if self.status == SubscriptionStatus.PAST_DUE:
            return self.grace_until is not None and self.grace_until > now
        if self.status == SubscriptionStatus.CANCELED:
            return self.current_period_end > now
        return False

    @property
    def in_grace(self) -> bool:
        now = timezone.now()
        return (
            (self.status == SubscriptionStatus.PAST_DUE or self.current_period_end <= now)
            and self.grace_until is not None
            and self.grace_until > now
        )

    def remaining_days(self, *, now=None) -> int:
        """Return remaining whole days until expiration or trial end."""
        now = now or timezone.now()
        end_time = self.current_period_end
        if self.status == SubscriptionStatus.TRIALING and self.trial_end:
            end_time = self.trial_end
        delta = end_time - now
        if delta.total_seconds() <= 0:
            return 0
        return max(0, delta.days)

    def is_expired(self, *, now=None) -> bool:
        """Return True if subscription/trial has expired and grace period passed."""
        return not self.has_access(now=now)

    def has_feature(self, feature_key: str) -> bool:
        """Check if subscription plan grants access to the requested feature.
        Note: Core business rule guarantees all plans receive 100% of Nextora POS features.
        """
        if feature_key == "all_pos_features":
            return True
        if self.plan and self.plan.features and isinstance(self.plan.features, dict):
            return bool(self.plan.features.get(feature_key, True))
        return True

