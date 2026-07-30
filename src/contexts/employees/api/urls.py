from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    DepartmentViewSet,
    DesignationViewSet,
    EmployeeDashboardViewSet,
    EmployeeProfileViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    PayrollViewSet,
    PerformanceReviewViewSet,
    ShiftViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("designations", DesignationViewSet, basename="designation")
router.register("profiles", EmployeeProfileViewSet, basename="profiles")
router.register("employees", EmployeeProfileViewSet, basename="employees")
router.register("shifts", ShiftViewSet, basename="shifts")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("leaves", LeaveRequestViewSet, basename="leaves")
router.register("payroll", PayrollViewSet, basename="payroll")
router.register("performance", PerformanceReviewViewSet, basename="performance")
router.register("dashboard", EmployeeDashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
