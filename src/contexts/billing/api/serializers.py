from rest_framework import serializers

from contexts.billing.models.invoice import SubscriptionInvoice
from contexts.billing.models.plan import Plan
from contexts.billing.models.subscription import Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "code", "description", "price", "billing_interval",
            "trial_days", "features", "is_active",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "trial_start", "trial_end",
            "current_period_start", "current_period_end", "cancel_at_period_end",
            "canceled_at", "ended_at",
        ]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    """Serialiser for platform subscription invoices issued to tenants."""

    class Meta:
        model = SubscriptionInvoice
        fields = [
            "id", "number", "status", "due_at", "paid_at",
            "amount", "tax_amount", "total", "currency",
            "period_start", "period_end",
        ]


# Alias kept for backwards compat with views import
InvoiceSerializer = SubscriptionInvoiceSerializer
