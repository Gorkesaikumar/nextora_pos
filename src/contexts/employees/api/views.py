from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Attendance, EmployeeProfile, LeaveRequest, Shift
from ..services import clock_in, clock_out, process_leave_request
from .serializers import (
    AttendanceSerializer,
    EmployeeProfileSerializer,
    LeaveRequestSerializer,
    ShiftSerializer,
)


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmployeeProfile.objects.all()


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Shift.objects.all()


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Attendance.objects.all()

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        profile = EmployeeProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"detail": "No Employee profile found for the active user session."},
                status=status.HTTP_404_NOT_FOUND,
            )

        shift_id = request.data.get("shift_id")
        attendance = clock_in(profile.id, shift_id=shift_id)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        attendance = clock_out(pk)
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.all()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        reviewer = EmployeeProfile.objects.filter(user=request.user).first()
        if not reviewer:
            return Response(
                {"detail": "Reviewer profile not found for active session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        leave = process_leave_request(pk, reviewer_id=reviewer.id, is_approved=True)
        serializer = self.get_serializer(leave)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        reviewer = EmployeeProfile.objects.filter(user=request.user).first()
        if not reviewer:
            return Response(
                {"detail": "Reviewer profile not found for active session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        leave = process_leave_request(pk, reviewer_id=reviewer.id, is_approved=False)
        serializer = self.get_serializer(leave)
        return Response(serializer.data, status=status.HTTP_200_OK)
