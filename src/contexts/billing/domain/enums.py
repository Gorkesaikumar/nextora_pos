"""Billing enumerations.

Kept as Django TextChoices so they double as model `choices` and as importable
constants for the service layer (single source of truth for status strings).
"""
from django.db import models


class BillingInterval(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    HALF_YEARLY = "half_yearly", "Half-Yearly"
    YEARLY = "yearly", "Yearly"
    CUSTOM = "custom", "Custom Duration"


class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage (%)"
    FLAT = "flat", "Flat Amount (₹)"


class DiscountScope(models.TextChoices):
    PLATFORM = "platform", "Entire Platform"
    TENANT = "tenant", "Specific Restaurant"
    PLAN = "plan", "Specific Plan"


class CouponEligibility(models.TextChoices):
    ALL = "all", "All Customers"
    NEW_ONLY = "new_only", "New Customers Only"
    EXISTING = "existing", "Existing Customers Only"
    TRIAL_USERS = "trial_users", "Trial Users Only"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"     # unpaid; may still have access during grace
    CANCELED = "canceled"     # will not renew; access until period end
    EXPIRED = "expired"       # access revoked
    INCOMPLETE = "incomplete" # pending first payment (checkout session active)

    @classmethod
    def occupied(cls) -> list[str]:
        """Statuses that count as 'a live subscription' (one-per-tenant rule)."""
        return [cls.TRIALING, cls.ACTIVE, cls.PAST_DUE]


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft"
    OPEN = "open"            # issued, awaiting payment
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class PaymentStatus(models.TextChoices):
    PENDING = "pending"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
