import datetime
import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from shared.tenancy.scope import tenant_scope
from .models import (
    Attendance,
    AttendanceStatus,
    EmployeeProfile,
    LeaveRequest,
    LeaveStatus,
    PayoutStatus,
    SalaryPayout,
    Shift,
)

logger = logging.getLogger(__name__)


def clock_in(employee_id: UUID, shift_id: UUID | None = None) -> Attendance:
    """Logs check-in time and evaluates PRESENT vs LATE status based on shift."""
    now = timezone.now()
    local_date = timezone.localdate()

    with transaction.atomic():
        # Prevent duplicate check-in for the same date
        existing = Attendance.objects.filter(employee_id=employee_id, date=local_date).first()
        if existing:
            return existing

        status = AttendanceStatus.PRESENT
        if shift_id:
            try:
                shift = Shift.objects.get(id=shift_id)
                # Convert time bounds and buffer 15 mins for late arrival
                shift_start = datetime.datetime.combine(local_date, shift.start_time)
                check_in_local = timezone.localtime(now)
                late_threshold = shift_start + datetime.timedelta(minutes=15)
                
                if check_in_local.replace(tzinfo=None) > late_threshold:
                    status = AttendanceStatus.LATE
            except Shift.DoesNotExist:
                pass

        attendance = Attendance.objects.create(
            employee_id=employee_id, date=local_date, check_in=now, status=status
        )

    return attendance


def clock_out(attendance_id: UUID) -> Attendance:
    """Registers checkout time."""
    now = timezone.now()
    with transaction.atomic():
        attendance = Attendance.objects.select_for_update().get(id=attendance_id)
        if not attendance.check_out:
            attendance.check_out = now
            attendance.save(update_fields=["check_out", "updated_at"])

    return attendance


def process_leave_request(request_id: UUID, reviewer_id: UUID, is_approved: bool) -> LeaveRequest:
    """Approves or rejects a leave request and stamps the reviewer."""
    status = LeaveStatus.APPROVED if is_approved else LeaveStatus.REJECTED
    with transaction.atomic():
        leave = LeaveRequest.objects.select_for_update().get(id=request_id)
        leave.status = status
        leave.approved_by_id = reviewer_id
        leave.save(update_fields=["status", "approved_by", "updated_at"])

    return leave


def run_payroll(tenant_id: UUID, period_start: datetime.date, period_end: datetime.date) -> int:
    """Sweeps all active employee profiles and creates PENDING SalaryPayout records."""
    payout_count = 0
    with tenant_scope(tenant_id):
        employees = EmployeeProfile.objects.filter(is_active=True)

        with transaction.atomic():
            for emp in employees:
                # Prevent duplicate payout records for the same period
                exists = SalaryPayout.objects.filter(
                    employee=emp, period_start=period_start, period_end=period_end
                ).exists()
                if not exists:
                    SalaryPayout.objects.create(
                        employee=emp,
                        period_start=period_start,
                        period_end=period_end,
                        amount=emp.base_salary,
                        status=PayoutStatus.PENDING,
                    )
                    payout_count += 1

    return payout_count
