from django.db import models
from shared.tenancy.models import TenantAwareModel
from .core import EmployeeProfile, Department


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    LATE = "late", "Late"
    HALF_DAY = "half_day", "Half Day"
    ABSENT = "absent", "Absent"


class Shift(TenantAwareModel):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    grace_period_minutes = models.PositiveIntegerField(default=15, help_text="Late mark after this grace period")
    break_time_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_shift"

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time} - {self.end_time})"


class WeekDay(models.IntegerChoices):
    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class WeeklyOff(TenantAwareModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="weekly_offs", help_text="Apply to whole department if set")
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="weekly_offs", help_text="Apply to specific employee if set")
    day_of_week = models.IntegerField(choices=WeekDay.choices)
    is_alternate = models.BooleanField(default=False, help_text="E.g., Alternate Saturdays")

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_weekly_off"

    def __str__(self) -> str:
        target = self.employee.full_name if self.employee else (self.department.name if self.department else "Tenant Level")
        alt = "Alternate " if self.is_alternate else ""
        return f"{target} - {alt}{self.get_day_of_week_display()}"


class Attendance(TenantAwareModel):
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name="attendance_logs"
    )
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    is_late_entry = models.BooleanField(default=False)
    is_early_exit = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=False, help_text="Manually added/corrected by admin")
    device_id = models.CharField(max_length=100, blank=True, help_text="For Biometric/QR integration")
    notes = models.TextField(blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "employee_attendance"
        indexes = [
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee.full_name} - {self.date} ({self.status})"
