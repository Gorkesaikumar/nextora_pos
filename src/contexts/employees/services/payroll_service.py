import datetime
from uuid import UUID
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

from shared.tenancy.scope import tenant_scope
from contexts.employees.models import (
    EmployeeProfile,
    SalaryPayout,
    PayoutStatus,
    PayoutComponent,
    Attendance,
    AttendanceStatus
)


def run_payroll(tenant_id: UUID, period_start: datetime.date, period_end: datetime.date) -> int:
    """Sweeps all active employee profiles and creates PENDING SalaryPayout records based on attendance."""
    payout_count = 0
    with tenant_scope(tenant_id):
        employees = EmployeeProfile.objects.filter(status='active').select_related('designation')

        with transaction.atomic():
            for emp in employees:
                # Prevent duplicate payout records for the same period
                exists = SalaryPayout.objects.filter(
                    employee=emp, period_start=period_start, period_end=period_end
                ).exists()
                if exists:
                    continue

                base = emp.base_salary or Decimal('0.00')
                
                # Basic mock logic for deductions based on attendance
                # In a real HRMS, this would check attendance vs shift rules
                absences = Attendance.objects.filter(
                    employee=emp, 
                    date__gte=period_start, 
                    date__lte=period_end, 
                    status=AttendanceStatus.ABSENT
                ).count()
                
                # Simple per-day deduction for absences
                daily_rate = base / 30
                deduction = daily_rate * absences

                payout = SalaryPayout.objects.create(
                    employee=emp,
                    period_start=period_start,
                    period_end=period_end,
                    base_amount=base,
                    total_earnings=base,
                    total_deductions=deduction,
                    net_payable=base - deduction,
                    status=PayoutStatus.PENDING,
                )
                
                # Create components
                PayoutComponent.objects.create(
                    payout=payout,
                    name="Base Salary",
                    component_type="earning",
                    amount=base
                )
                
                if deduction > 0:
                    PayoutComponent.objects.create(
                        payout=payout,
                        name="Unpaid Absences",
                        component_type="deduction",
                        amount=deduction
                    )
                
                payout_count += 1

    return payout_count
