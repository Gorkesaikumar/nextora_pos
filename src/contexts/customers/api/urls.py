from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CouponViewSet, CustomerViewSet

router = DefaultRouter()
router.register("profiles", CustomerViewSet, basename="profiles")
router.register("coupons", CouponViewSet, basename="coupons")

urlpatterns = [
    path("", include(router.urls)),
]
