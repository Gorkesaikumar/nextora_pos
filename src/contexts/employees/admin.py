from django.contrib import admin

from .models import (
    Attendance,
    EmployeeProfile,
    LeaveRequest,
    PerformanceReview,
    SalaryPayout,
    Shift,
)


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    readonly_fields = ["date", "check_in", "check_out", "status"]


class LeaveRequestInline(admin.TabularInline):
    model = LeaveRequest
    fk_name = "employee"
    extra = 0


class PerformanceReviewInline(admin.TabularInline):
    model = PerformanceReview
    fk_name = "employee"
    extra = 0


class SalaryPayoutInline(admin.TabularInline):
    model = SalaryPayout
    extra = 0


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "job_title",
        "tenant",
        "location_id",
        "base_salary",
        "hire_date",
        "is_active",
    ]
    list_filter = ["is_active", "job_title"]
    search_fields = ["user__email", "job_title"]
    inlines = [AttendanceInline, LeaveRequestInline, PerformanceReviewInline, SalaryPayoutInline]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "start_time", "end_time"]
    search_fields = ["name"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "date", "check_in", "check_out", "status"]
    list_filter = ["status", "date"]
    search_fields = ["employee__user__email"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "start_date", "end_date", "leave_type", "status", "approved_by"]
    list_filter = ["status", "leave_type"]
    search_fields = ["employee__user__email"]


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ["employee", "reviewer", "review_date", "rating"]
    list_filter = ["rating", "review_date"]
    search_fields = ["employee__user__email"]


@admin.register(SalaryPayout)
class SalaryPayoutAdmin(admin.ModelAdmin):
    list_display = ["employee", "period_start", "period_end", "amount", "status", "paid_at"]
    list_filter = ["status", "period_start"]
    search_fields = ["employee__user__email"]
