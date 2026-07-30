from rest_framework.routers import DefaultRouter

from contexts.catalog.api.views import (
    CategoryViewSet,
    ComboOfferViewSet,
    ModifierGroupViewSet,
    ModifierViewSet,
    PriceTierViewSet,
    ProductVariantViewSet,
    ProductViewSet,
    TaxClassViewSet,
    UnitViewSet,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("variants", ProductVariantViewSet, basename="variant")
router.register("modifier-groups", ModifierGroupViewSet, basename="modifier-group")
router.register("modifiers", ModifierViewSet, basename="modifier")
router.register("combos", ComboOfferViewSet, basename="combo")
router.register("price-tiers", PriceTierViewSet, basename="price-tier")
router.register("taxes", TaxClassViewSet, basename="tax")
router.register("units", UnitViewSet, basename="unit")

urlpatterns = router.urls
