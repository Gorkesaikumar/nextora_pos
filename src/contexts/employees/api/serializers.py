from rest_framework import serializers

from ..models import Attendance, EmployeeProfile, LeaveRequest, Shift


class EmployeeProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "email",
            "full_name",
            "location_id",
            "job_title",
            "base_salary",
            "hire_date",
            "is_active",
        ]
        read_only_fields = ["id", "email", "full_name"]


class ShiftSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shift
        fields = ["id", "name", "start_time", "end_time"]


class AttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attendance
        fields = ["id", "employee", "date", "check_in", "check_out", "status"]
        read_only_fields = ["id", "date", "check_in", "check_out", "status"]


class LeaveRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = LeaveRequest
        fields = ["id", "employee", "start_date", "end_date", "leave_type", "status", "approved_by"]
        read_only_fields = ["id", "status", "approved_by"]
