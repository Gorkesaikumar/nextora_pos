from rest_framework.routers import DefaultRouter

from .views import CouponViewSet, CustomerViewSet, LoyaltyProgramViewSet

router = DefaultRouter()
router.register("profiles", CustomerViewSet, basename="customer")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("loyalty", LoyaltyProgramViewSet, basename="loyalty-program")

urlpatterns = router.urls
