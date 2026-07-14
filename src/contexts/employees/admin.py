from django.contrib import admin

from .models import (
    Attendance,
    Department,
    Designation,
    EmployeeProfile,
    EmployeeDocument,
    LeaveBalance,
    LeaveRequest,
    PerformanceReview,
    SalaryPayout,
    PayoutComponent,
    Shift,
    WeeklyOff,
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "is_active"]
    search_fields = ["name"]
    list_filter = ["is_active"]

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "tenant", "is_active"]
    search_fields = ["name"]
    list_filter = ["is_active", "department"]


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0


class LeaveBalanceInline(admin.TabularInline):
    model = LeaveBalance
    extra = 0


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = [
        "employee_code",
        "first_name",
        "last_name",
        "department",
        "designation",
        "tenant",
        "base_salary",
        "status",
    ]
    list_filter = ["status", "department", "designation", "employment_type"]
    search_fields = ["employee_code", "first_name", "last_name", "email"]
    inlines = [EmployeeDocumentInline, LeaveBalanceInline]


class WeeklyOffInline(admin.TabularInline):
    model = WeeklyOff
    extra = 0

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "start_time", "end_time", "grace_period_minutes"]
    search_fields = ["name"]

@admin.register(WeeklyOff)
class WeeklyOffAdmin(admin.ModelAdmin):
    list_display = ["__str__", "day_of_week", "is_alternate"]
    list_filter = ["day_of_week", "is_alternate"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "date", "shift", "check_in", "check_out", "status", "is_late_entry"]
    list_filter = ["status", "date", "is_late_entry", "is_early_exit"]
    search_fields = ["employee__first_name", "employee__last_name"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "start_date", "end_date", "leave_type", "status"]
    list_filter = ["status", "leave_type"]
    search_fields = ["employee__first_name", "employee__last_name"]


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ["employee", "reviewer", "review_date", "rating"]
    list_filter = ["rating", "review_date"]
    search_fields = ["employee__first_name", "employee__last_name"]


class PayoutComponentInline(admin.TabularInline):
    model = PayoutComponent
    extra = 0

@admin.register(SalaryPayout)
class SalaryPayoutAdmin(admin.ModelAdmin):
    list_display = ["employee", "period_start", "period_end", "net_payable", "status", "paid_at"]
    list_filter = ["status", "period_start"]
    search_fields = ["employee__first_name", "employee__last_name"]
    inlines = [PayoutComponentInline]
