from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet, SubscriptionViewSet
from .webhooks import razorpay_webhook

app_name = "saas_billing"

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("webhooks/billing/razorpay/", razorpay_webhook, name="razorpay-webhook"),
    path("api/v1/billing/", include(router.urls)),
]
