from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contexts.ordering.api.offline_views import (
    OfflineBootstrapAPIView,
    OfflineSyncAPIView,
)
from contexts.ordering.api.views import (
    CartViewSet,
    KOTViewSet,
    OrderViewSet,
    PaymentViewSet,
    PrintJobViewSet,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("cart", CartViewSet, basename="cart")
router.register("kot", KOTViewSet, basename="kot")
router.register("print-queue", PrintJobViewSet, basename="print-queue")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("offline/bootstrap/", OfflineBootstrapAPIView.as_view(), name="offline_bootstrap"),
    path("offline/sync/", OfflineSyncAPIView.as_view(), name="offline_sync"),
    path("", include(router.urls)),
]

