from django.db import models
from shared.tenancy.models import TenantAwareModel
from .core import EmployeeProfile


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
    
    # Tracked Metrics
    orders_handled = models.PositiveIntegerField(default=0)
    tables_served = models.PositiveIntegerField(default=0)
    revenue_generated = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_count = models.PositiveIntegerField(default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    leaves_taken = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_performance_review"

    def __str__(self) -> str:
        return (
            f"{self.employee.full_name} Review by {self.reviewer.full_name} on {self.review_date}"
        )
