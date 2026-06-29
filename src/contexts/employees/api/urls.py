from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceViewSet, EmployeeProfileViewSet, LeaveRequestViewSet, ShiftViewSet

router = DefaultRouter()
router.register("profiles", EmployeeProfileViewSet, basename="profiles")
router.register("shifts", ShiftViewSet, basename="shifts")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("leaves", LeaveRequestViewSet, basename="leaves")

urlpatterns = [
    path("", include(router.urls)),
]
