from rest_framework.routers import DefaultRouter

from .views import ProductViewSet
# app_name removed to prevent conflict with web namespace
router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls
