"""Restaurant API URL routing."""
from rest_framework.routers import DefaultRouter

from .views import (
    BranchViewSet,
    CashCounterViewSet,
    DiningTableViewSet,
    HolidayViewSet,
    KitchenStationViewSet,
    PrinterViewSet,
    RestaurantViewSet,
)

router = DefaultRouter()
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("branches", BranchViewSet, basename="branch")
router.register("tables", DiningTableViewSet, basename="dining-table")
router.register("stations", KitchenStationViewSet, basename="kitchen-station")
router.register("printers", PrinterViewSet, basename="printer")
router.register("counters", CashCounterViewSet, basename="cash-counter")
router.register("holidays", HolidayViewSet, basename="holiday")

urlpatterns = router.urls
