from rest_framework import serializers

from ..models import (
    Attendance,
    Department,
    Designation,
    EmployeeProfile,
    LeaveBalance,
    LeaveRequest,
    PayoutComponent,
    PerformanceReview,
    SalaryPayout,
    Shift,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Designation
        fields = ["id", "name", "department", "department_name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "department_name", "created_at"]


class EmployeeProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id", "user", "employee_code", "first_name", "last_name", "full_name",
            "department", "department_name", "designation", "designation_name",
            "employment_type", "status", "hire_date", "base_salary", "hourly_rate",
            "mobile_number", "email", "gender", "date_of_birth"
        ]
        read_only_fields = ["id", "full_name", "department_name", "designation_name"]

    def get_full_name(self, obj):
        return obj.full_name


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["id", "name", "start_time", "end_time", "grace_period_minutes", "break_time_minutes", "is_active"]


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id", "employee", "employee_name", "shift", "shift_name", "date", 
            "check_in", "check_out", "break_start", "break_end", "status",
            "is_late_entry", "is_early_exit", "is_manual", "notes"
        ]
        read_only_fields = ["id", "employee_name", "shift_name", "date", "status", "is_late_entry", "is_early_exit"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "employee", "year", "leave_type", "allocated", "used", "remaining"]
        read_only_fields = ["id", "remaining"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "start_date", "end_date", "leave_type",
            "status", "reason", "rejection_reason", "manager_approved_by", "owner_approved_by"
        ]
        read_only_fields = ["id", "status", "manager_approved_by", "owner_approved_by", "rejection_reason", "employee_name"]


class PayoutComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutComponent
        fields = ["id", "payout", "name", "type", "amount"]
        read_only_fields = ["id"]


class SalaryPayoutSerializer(serializers.ModelSerializer):
    components = PayoutComponentSerializer(many=True, read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = SalaryPayout
        fields = [
            "id", "employee", "employee_name", "period_start", "period_end", "base_amount",
            "total_earnings", "total_deductions", "net_payable", "status", "paid_at", "components"
        ]
        read_only_fields = ["id", "employee_name", "total_earnings", "total_deductions", "net_payable"]


class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)

    class Meta:
        model = PerformanceReview
        fields = [
            "id", "employee", "employee_name", "reviewer", "reviewer_name", "review_date",
            "rating", "comments", "orders_handled", "tables_served", "revenue_generated",
            "attendance_percentage", "late_count", "overtime_hours", "leaves_taken"
        ]
        read_only_fields = ["id", "employee_name", "reviewer_name"]
