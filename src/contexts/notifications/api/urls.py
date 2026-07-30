"""URL Routing for Notifications API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationTemplateViewSet,
    NotificationViewSet,
    InAppNotificationViewSet,
    DispatchNotificationView,
    SendReceiptView
)

app_name = "notifications_api"

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="notification-template")
router.register("history", NotificationViewSet, basename="notification-history")
router.register("inbox", InAppNotificationViewSet, basename="notification-inbox")

urlpatterns = [
    path("", include(router.urls)),
    path("dispatch/", DispatchNotificationView.as_view(), name="notification-dispatch"),
    path("receipt/", SendReceiptView.as_view(), name="notification-receipt"),
]
