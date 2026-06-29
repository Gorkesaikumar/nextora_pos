"""Restaurant API ViewSets."""
import datetime
import uuid

from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Branch,
    BranchGSTProfile,
    BranchSettings,
    BusinessHours,
    CashCounter,
    DiningTable,
    Holiday,
    KitchenStation,
    Printer,
    Restaurant,
)
from ..services import (
    activate_restaurant,
    block_table,
    check_branch_open_status,
    close_restaurant,
    create_branch,
    create_restaurant,
    ensure_default_restaurant,
    generate_table_qr_url,
    merge_tables,
    open_branch,
    pause_branch,
    permanently_close_branch,
    reactivate_restaurant,
    release_table,
    resume_branch,
    seat_guests,
    set_business_hours,
    split_tables,
    suspend_restaurant,
    update_gst_profile,
)
from .serializers import (
    BranchGSTProfileSerializer,
    BranchSerializer,
    BranchSettingsSerializer,
    BusinessHoursInputSerializer,
    BusinessHoursSerializer,
    CashCounterSerializer,
    DiningTableSerializer,
    GSTProfileInputSerializer,
    HolidaySerializer,
    KitchenStationSerializer,
    MergeTablesInputSerializer,
    PrinterSerializer,
    RestaurantSerializer,
)


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Restaurant.objects.all()

    def perform_create(self, serializer):
        tenant_id = self.request.META.get("HTTP_X_TENANT_ID") or getattr(self.request, "tenant_id", None)
        # Fallback to resolver current tenant
        if not tenant_id:
            from shared.tenancy.context import get_current_tenant
            tenant_id = get_current_tenant()
            
        serializer.save(tenant_id=tenant_id)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            restaurant = activate_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        try:
            restaurant = suspend_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        try:
            restaurant = reactivate_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        try:
            restaurant = close_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Branch.objects.all()

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        try:
            branch = open_branch(uuid.UUID(pk))
            return Response(self.get_serializer(branch).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        try:
            branch = pause_branch(uuid.UUID(pk))
            return Response(self.get_serializer(branch).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        try:
            branch = resume_branch(uuid.UUID(pk))
            return Response(self.get_serializer(branch).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def close_permanently(self, request, pk=None):
        try:
            branch = permanently_close_branch(uuid.UUID(pk))
            return Response(self.get_serializer(branch).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="gst-profile")
    def set_gst_profile(self, request, pk=None):
        serializer = GSTProfileInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        
        try:
            profile = update_gst_profile(
                branch_id=uuid.UUID(pk),
                gstin=d["gstin"],
                legal_name=d["legal_name"],
                registration_type=d["registration_type"],
            )
            return Response(BranchGSTProfileSerializer(profile).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="business-hours")
    def set_business_hours(self, request, pk=None):
        serializer = BusinessHoursInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        
        try:
            hours = set_business_hours(
                branch_id=uuid.UUID(pk),
                day_of_week=d["day_of_week"],
                open_time=d["open_time"],
                close_time=d["close_time"],
                is_closed=d.get("is_closed", False),
            )
            return Response(BusinessHoursSerializer(hours).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="open-status")
    def open_status(self, request, pk=None):
        time_str = request.query_params.get("time")
        if time_str:
            dt = datetime.datetime.fromisoformat(time_str)
        else:
            dt = datetime.datetime.now()
            
        is_open, reason = check_branch_open_status(uuid.UUID(pk), dt)
        return Response({"is_open": is_open, "reason": reason})



class DiningTableViewSet(viewsets.ModelViewSet):
    serializer_class = DiningTableSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DiningTable.objects.all()

    @action(detail=True, methods=["post"])
    def seat(self, request, pk=None):
        try:
            table = seat_guests(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reserve(self, request, pk=None):
        try:
            table = reserve_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        try:
            table = release_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        try:
            table = block_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        serializer = MergeTablesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            table = merge_tables(
                primary_table_id=uuid.UUID(pk),
                secondary_table_ids=serializer.validated_data["secondary_table_ids"],
            )
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def split(self, request, pk=None):
        try:
            table = split_tables(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="generate-qr")
    def generate_qr(self, request, pk=None):
        try:
            qr_url = generate_table_qr_url(uuid.UUID(pk))
            return Response({"qr_code_url": qr_url})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class KitchenStationViewSet(viewsets.ModelViewSet):
    serializer_class = KitchenStationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return KitchenStation.objects.all()


class PrinterViewSet(viewsets.ModelViewSet):
    serializer_class = PrinterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Printer.objects.all()


class CashCounterViewSet(viewsets.ModelViewSet):
    serializer_class = CashCounterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CashCounter.objects.all()


class HolidayViewSet(viewsets.ModelViewSet):
    serializer_class = HolidaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Holiday.objects.all()
