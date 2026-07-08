from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, ModifierGroupViewSet, ModifierViewSet
# app_name removed to prevent conflict with web namespace
router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("modifier-groups", ModifierGroupViewSet, basename="modifier-group")
router.register("modifiers", ModifierViewSet, basename="modifier")

urlpatterns = router.urls
