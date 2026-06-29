from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from contexts.billing.api.serializers import InvoiceSerializer, SubscriptionSerializer
from contexts.billing.models.invoice import SubscriptionInvoice
from contexts.billing.models.subscription import Subscription
from contexts.identity.api.permissions import RequirePermission


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return Subscription.objects.select_related("plan").all()

    def get_permissions(self):
        return [IsAuthenticated(), RequirePermission("billing.view")()]


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return SubscriptionInvoice.objects.select_related("subscription").all()

    def get_permissions(self):
        return [IsAuthenticated(), RequirePermission("billing.view")()]
