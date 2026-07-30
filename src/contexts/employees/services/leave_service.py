import datetime
from uuid import UUID
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from contexts.employees.models import LeaveRequest, LeaveBalance, LeaveStatus


def get_leave_balance(employee_id: UUID, year: int) -> dict:
    balances = LeaveBalance.objects.filter(employee_id=employee_id, year=year)
    return {lb.leave_type: {"allocated": lb.allocated, "used": lb.used, "remaining": lb.remaining} for lb in balances}


def process_leave_request(request_id: UUID, reviewer_id: UUID, is_approved: bool, reason: str = "") -> LeaveRequest:
    """Approves or rejects a leave request and stamps the reviewer. If approved, updates leave balance."""
    status = LeaveStatus.APPROVED if is_approved else LeaveStatus.REJECTED
    
    with transaction.atomic():
        leave = LeaveRequest.objects.select_for_update().get(id=request_id)
        
        if leave.status not in (LeaveStatus.PENDING_MANAGER, LeaveStatus.PENDING_OWNER):
            return leave
            
        leave.status = status
        leave.manager_approved_by_id = reviewer_id
        if not is_approved:
            leave.rejection_reason = reason
        
        leave.save(update_fields=["status", "manager_approved_by", "rejection_reason", "updated_at"])

        if is_approved:
            days = (leave.end_date - leave.start_date).days + 1
            balance, _ = LeaveBalance.objects.get_or_create(
                employee_id=leave.employee_id,
                year=leave.start_date.year,
                leave_type=leave.leave_type,
                defaults={'allocated': 15.0, 'used': 0.0}
            )
            balance.used += days
            balance.save(update_fields=["used"])

    return leave
