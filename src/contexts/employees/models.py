from django.conf import settings
from django.db import models
from shared.tenancy.models import TenantAwareModel


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    LATE = "late", "Late"
    ABSENT = "absent", "Absent"


class LeaveType(models.TextChoices):
    SICK = "sick", "Sick Leave"
    CASUAL = "casual", "Casual Leave"
    UNPAID = "unpaid", "Unpaid Leave"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"


class EmployeeProfile(TenantAwareModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profiles"
    )
    location_id = models.UUIDField(null=True, blank=True, help_text="Soft branch reference")
    job_title = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"],
                name="uq_employee_profile__tenant_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.job_title}"


class Shift(TenantAwareModel):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_shift"

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time} - {self.end_time})"


class Attendance(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="attendance_logs"
    )
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_attendance"
        indexes = [
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.user.email} - {self.date} ({self.status})"


class LeaveRequest(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="leave_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    status = models.CharField(
        max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING
    )
    approved_by = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_leave_request"

    def __str__(self) -> str:
        return f"{self.employee.user.email} - {self.start_date} to {self.end_date} ({self.status})"


class PerformanceReview(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        EmployeeProfile, on_delete=models.PROTECT, related_name="conducted_reviews"
    )
    review_date = models.DateField(db_index=True)
    rating = models.PositiveIntegerField(help_text="Rating from 1 to 5")
    comments = models.TextField()

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_performance_review"

    def __str__(self) -> str:
        return (
            f"{self.employee.user.email} Review by {self.reviewer.user.email} on {self.review_date}"
        )


class SalaryPayout(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="salary_payouts"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_salary_payout"

    def __str__(self) -> str:
        return (
            f"{self.employee.user.email} - Payout {self.period_start} to {self.period_end}"
            f" ({self.status})"
        )
