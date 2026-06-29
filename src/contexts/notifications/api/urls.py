from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InAppInboxViewSet, TwilioWebhookView

router = DefaultRouter()
router.register("inbox", InAppInboxViewSet, basename="inbox")

urlpatterns = [
    path("", include(router.urls)),
    path("webhooks/twilio/", TwilioWebhookView.as_view(), name="webhook-twilio"),
]
