from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contexts.ordering.api.offline_views import (
    OfflineBootstrapAPIView,
    OfflineSyncAPIView,
)
from contexts.ordering.api.views import OrderViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("offline/bootstrap/", OfflineBootstrapAPIView.as_view(), name="offline_bootstrap"),
    path("offline/sync/", OfflineSyncAPIView.as_view(), name="offline_sync"),
    path("", include(router.urls)),
]
