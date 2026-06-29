"""Billing enumerations.

Kept as Django TextChoices so they double as model `choices` and as importable
constants for the service layer (single source of truth for status strings).
"""
from django.db import models


class BillingInterval(models.TextChoices):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"     # unpaid; may still have access during grace
    CANCELED = "canceled"     # will not renew; access until period end
    EXPIRED = "expired"       # access revoked

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
