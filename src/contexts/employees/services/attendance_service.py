import datetime
from uuid import UUID
from django.db import transaction
from django.utils import timezone

from contexts.employees.models import Attendance, AttendanceStatus, Shift


def clock_in(employee_id: UUID, shift_id: UUID | None = None, device_id: str = "") -> Attendance:
    """Logs check-in time and evaluates PRESENT vs LATE status based on shift."""
    now = timezone.now()
    local_date = timezone.localdate()

    with transaction.atomic():
        # Check if already clocked in
        existing = Attendance.objects.filter(employee_id=employee_id, date=local_date).first()
        if existing:
            return existing

        status = AttendanceStatus.PRESENT
        is_late_entry = False
        
        if shift_id:
            try:
                shift = Shift.objects.get(id=shift_id)
                # Apply grace period logic
                shift_start = datetime.datetime.combine(local_date, shift.start_time)
                check_in_local = timezone.localtime(now)
                late_threshold = shift_start + datetime.timedelta(minutes=shift.grace_period_minutes)
                
                if check_in_local.replace(tzinfo=None) > late_threshold:
                    status = AttendanceStatus.LATE
                    is_late_entry = True
            except Shift.DoesNotExist:
                shift = None
        else:
            shift = None

        attendance = Attendance.objects.create(
            employee_id=employee_id, 
            date=local_date, 
            check_in=now, 
            status=status,
            shift=shift,
            is_late_entry=is_late_entry,
            device_id=device_id
        )

    return attendance


def clock_out(attendance_id: UUID, device_id: str = "") -> Attendance:
    """Registers checkout time and calculates early exit."""
    now = timezone.now()
    with transaction.atomic():
        attendance = Attendance.objects.select_for_update().get(id=attendance_id)
        if not attendance.check_out:
            attendance.check_out = now
            
            # Check for early exit
            if attendance.shift:
                shift_end = datetime.datetime.combine(attendance.date, attendance.shift.end_time)
                check_out_local = timezone.localtime(now).replace(tzinfo=None)
                if check_out_local < shift_end:
                    attendance.is_early_exit = True
                    
            attendance.save(update_fields=["check_out", "is_early_exit", "updated_at"])

    return attendance


def start_break(attendance_id: UUID) -> Attendance:
    now = timezone.now()
    with transaction.atomic():
        attendance = Attendance.objects.select_for_update().get(id=attendance_id)
        if not attendance.break_start:
            attendance.break_start = now
            attendance.save(update_fields=["break_start", "updated_at"])
    return attendance


def end_break(attendance_id: UUID) -> Attendance:
    now = timezone.now()
    with transaction.atomic():
        attendance = Attendance.objects.select_for_update().get(id=attendance_id)
        if attendance.break_start and not attendance.break_end:
            attendance.break_end = now
            attendance.save(update_fields=["break_end", "updated_at"])
    return attendance
