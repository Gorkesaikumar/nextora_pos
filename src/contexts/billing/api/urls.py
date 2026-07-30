from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet, SubscriptionViewSet, PlanViewSet, RazorpayOrderView, RazorpayVerifyView
from .webhooks import razorpay_webhook

app_name = "saas_billing"

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("plans", PlanViewSet, basename="plan")

urlpatterns = [
    path("webhooks/billing/razorpay/", razorpay_webhook, name="razorpay-webhook"),
    path("api/v1/billing/orders/", RazorpayOrderView.as_view(), name="create_order"),
    path("api/v1/billing/verify-payment/", RazorpayVerifyView.as_view(), name="verify_payment"),
    path("api/v1/billing/", include(router.urls)),
]
