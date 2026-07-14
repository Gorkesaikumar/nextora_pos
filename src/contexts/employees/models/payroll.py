from django.db import models
from shared.tenancy.models import TenantAwareModel
from .core import EmployeeProfile


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"


class ComponentType(models.TextChoices):
    EARNING = "earning", "Earning"
    DEDUCTION = "deduction", "Deduction"


class SalaryPayout(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="salary_payouts"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Financial fields
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_salary_payout"

    def __str__(self) -> str:
        return (
            f"{self.employee.full_name} - {self.period_start} to {self.period_end}"
            f" ({self.status})"
        )


class PayoutComponent(TenantAwareModel):
    payout = models.ForeignKey(SalaryPayout, on_delete=models.CASCADE, related_name="components")
    name = models.CharField(max_length=100, help_text="e.g. Overtime, Tips, PF, Professional Tax, Unpaid Leave")
    type = models.CharField(max_length=20, choices=ComponentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_payout_component"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_type_display()}): {self.amount}"
