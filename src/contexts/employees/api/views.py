import uuid
import datetime
from decimal import Decimal

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.tenancy import get_current_tenant
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
    EmployeeStatus,
)
from ..services import (
    clock_in,
    clock_out,
    start_break,
    end_break,
    process_leave_request,
    run_payroll,
)
from .serializers import (
    AttendanceSerializer,
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeProfileSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    SalaryPayoutSerializer,
    PerformanceReviewSerializer,
    ShiftSerializer,
)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Department.objects.all()


class DesignationViewSet(viewsets.ModelViewSet):
    serializer_class = DesignationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Designation.objects.select_related("department").all()


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = EmployeeProfile.objects.select_related("department", "designation", "user")
        dept = self.request.query_params.get("department_id")
        if dept:
            qs = qs.filter(department_id=dept)
        return qs.all()


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Shift.objects.all()


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Attendance.objects.select_related("employee", "shift").all()

    def _resolve_employee(self, request):
        emp_id = request.data.get("employee_id") or request.query_params.get("employee_id")
        if emp_id:
            try:
                return EmployeeProfile.objects.get(id=emp_id)
            except EmployeeProfile.DoesNotExist:
                return None
        return EmployeeProfile.objects.filter(user=request.user).first()

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        return self._do_clock_in(request)

    @action(detail=False, methods=["post"], url_path="clock-in")
    def clock_in_action(self, request):
        return self._do_clock_in(request)

    def _do_clock_in(self, request):
        profile = self._resolve_employee(request)
        if not profile:
            return Response(
                {"detail": "No Employee profile found or specified for active session."},
                status=status.HTTP_404_NOT_FOUND,
            )

        shift_id = request.data.get("shift_id")
        device_id = request.data.get("device_id", "POS-TERMINAL")
        attendance = clock_in(profile.id, shift_id=shift_id, device_id=device_id)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        return self._do_clock_out(request, pk)

    @action(detail=True, methods=["post"], url_path="clock-out")
    def clock_out_action(self, request, pk=None):
        return self._do_clock_out(request, pk)

    def _do_clock_out(self, request, pk=None):
        device_id = request.data.get("device_id", "POS-TERMINAL")
        attendance = clock_out(pk, device_id=device_id)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="start-break")
    def start_break_action(self, request, pk=None):
        attendance = start_break(pk)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="end-break")
    def end_break_action(self, request, pk=None):
        attendance = end_break(pk)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeaveBalance.objects.select_related("employee").all()


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.select_related("employee").all()

    def _resolve_reviewer(self, request):
        # Prefer linked user profile, otherwise pick any manager/owner profile or fallback
        reviewer = EmployeeProfile.objects.filter(user=request.user).first()
        if not reviewer and request.data.get("reviewer_id"):
            reviewer = EmployeeProfile.objects.filter(id=request.data["reviewer_id"]).first()
        if not reviewer:
            reviewer = EmployeeProfile.objects.first()
        return reviewer

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        reviewer = self._resolve_reviewer(request)
        if not reviewer:
            return Response({"detail": "Reviewer profile not found."}, status=status.HTTP_403_FORBIDDEN)

        leave = process_leave_request(uuid.UUID(str(pk)), reviewer_id=reviewer.id, is_approved=True)
        serializer = self.get_serializer(leave)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        reviewer = self._resolve_reviewer(request)
        if not reviewer:
            return Response({"detail": "Reviewer profile not found."}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get("reason", "Rejected by reviewer.")
        leave = process_leave_request(uuid.UUID(str(pk)), reviewer_id=reviewer.id, is_approved=False, reason=reason)
        serializer = self.get_serializer(leave)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PayrollViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryPayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SalaryPayout.objects.select_related("employee").prefetch_related("components").all()

    @action(detail=False, methods=["post"], url_path="run")
    def run_payroll_action(self, request):
        tenant_id = get_current_tenant()
        period_start = request.data.get("period_start")
        period_end = request.data.get("period_end")
        
        if not period_start or not period_end:
            # Fallback to current month boundaries
            today = datetime.date.today()
            period_start = today.replace(day=1)
            period_end = today
        else:
            period_start = datetime.datetime.strptime(str(period_start), "%Y-%m-%d").date()
            period_end = datetime.datetime.strptime(str(period_end), "%Y-%m-%d").date()

        count = run_payroll(tenant_id, period_start, period_end)
        return Response({"success": True, "payouts_generated": count}, status=status.HTTP_201_CREATED)


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PerformanceReview.objects.select_related("employee", "reviewer").all()


class EmployeeDashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        today = datetime.date.today()
        total_employees = EmployeeProfile.objects.count()
        active_employees = EmployeeProfile.objects.filter(status=EmployeeStatus.ACTIVE).count()
        
        clocked_in_today = Attendance.objects.filter(date=today, check_out__isnull=True).count()
        leaves_today = LeaveRequest.objects.filter(
            start_date__lte=today, 
            end_date__gte=today, 
            status="approved"
        ).count()
        pending_leaves = LeaveRequest.objects.filter(
            status__in=["pending_manager", "pending_owner"]
        ).count()

        dept_count = Department.objects.filter(is_active=True).count()

        dashboard_data = {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "clocked_in_today": clocked_in_today,
            "employees_on_leave_today": leaves_today,
            "pending_leave_requests": pending_leaves,
            "active_departments": dept_count,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return Response(dashboard_data, status=status.HTTP_200_OK)
