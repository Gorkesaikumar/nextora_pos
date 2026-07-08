import uuid
from decimal import Decimal
from django.db import models

from shared.tenancy.models import TenantAwareModel

class RefundStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    COMPLETED = "COMPLETED", "Completed"
    REJECTED = "REJECTED", "Rejected"

class RefundType(models.TextChoices):
    PARTIAL = "PARTIAL", "Partial Refund"
    FULL = "FULL", "Full Refund"

class Refund(TenantAwareModel):
    """
    Records a financial refund against an established order/invoice.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey("ordering.Order", on_delete=models.PROTECT, related_name="refunds")
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    
    status = models.CharField(
        max_length=20, 
        choices=RefundStatus.choices, 
        default=RefundStatus.COMPLETED
    )
    refund_type = models.CharField(
        max_length=20, 
        choices=RefundType.choices, 
        default=RefundType.FULL
    )
    
    # Audit tracking
    requested_by = models.UUIDField(null=True, blank=True)
    approved_by = models.UUIDField(null=True, blank=True)
    
    class Meta(TenantAwareModel.Meta):
        db_table = "ordering_refund"
        ordering = ["-created_at"]
        
    def __str__(self) -> str:
        return f"Refund {self.id} for Order {self.order_id}"
