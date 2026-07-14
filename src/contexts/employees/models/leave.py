from django.db import models
from shared.tenancy.models import TenantAwareModel
from .core import EmployeeProfile


class LeaveType(models.TextChoices):
    SICK = "sick", "Sick Leave"
    CASUAL = "casual", "Casual Leave"
    PAID = "paid", "Paid Leave"
    UNPAID = "unpaid", "Loss Of Pay (LOP)"
    EMERGENCY = "emergency", "Emergency Leave"
    MATERNITY = "maternity", "Maternity/Paternity Leave"


class LeaveStatus(models.TextChoices):
    PENDING_MANAGER = "pending_manager", "Pending Manager Approval"
    PENDING_OWNER = "pending_owner", "Pending Owner Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class LeaveBalance(TenantAwareModel):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="leave_balances")
    year = models.PositiveIntegerField()
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "employee", "year", "leave_type"], name="uq_leave_balance")
        ]

    @property
    def remaining(self):
        return self.allocated - self.used

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.get_leave_type_display()} ({self.year})"


class LeaveRequest(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="leave_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    status = models.CharField(
        max_length=30, choices=LeaveStatus.choices, default=LeaveStatus.PENDING_MANAGER
    )
    reason = models.TextField(blank=True)
    
    manager_approved_by = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="manager_approved_leaves"
    )
    owner_approved_by = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="owner_approved_leaves"
    )
    rejection_reason = models.TextField(blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_leave_request"

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.start_date} to {self.end_date} ({self.status})"
