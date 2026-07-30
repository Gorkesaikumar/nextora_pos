"""Restaurant API ViewSets."""
import datetime
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.api.views import BaseModelViewSet
from contexts.restaurant.domain.enums import TableStatus
from ..models import (
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
    close_restaurant,
    create_restaurant,
    ensure_default_restaurant,
    generate_table_qr_url,
    merge_tables,
    reactivate_restaurant,
    release_table,
    reserve_table,
    seat_guests,
    split_tables,
    suspend_restaurant,
)
from ..services.hours_service import check_restaurant_open_status, set_business_hours
from .serializers import (
    BusinessHoursInputSerializer,
    BusinessHoursSerializer,
    CashCounterSerializer,
    DiningTableSerializer,
    FloorLayoutBatchUpdateSerializer,
    GSTProfileInputSerializer,
    HolidaySerializer,
    KitchenStationSerializer,
    MergeTablesInputSerializer,
    MoveTableInputSerializer,
    PrinterSerializer,
    RestaurantSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List all restaurants"),
    create=extend_schema(summary="Create a new restaurant"),
    retrieve=extend_schema(summary="Get restaurant details"),
    update=extend_schema(summary="Update restaurant details"),
    partial_update=extend_schema(summary="Partially update restaurant"),
    destroy=extend_schema(summary="Delete restaurant"),
)
class RestaurantViewSet(BaseModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return Restaurant.objects.all()

    def perform_create(self, serializer):
        tenant_id = self.request.META.get("HTTP_X_TENANT_ID") or getattr(self.request, "tenant_id", None)
        if not tenant_id:
            from shared.tenancy.context import get_current_tenant
            tenant_id = get_current_tenant()
        serializer.save(tenant_id=tenant_id)

    @extend_schema(summary="Activate restaurant", responses={200: RestaurantSerializer})
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            restaurant = activate_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Suspend restaurant", responses={200: RestaurantSerializer})
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        try:
            restaurant = suspend_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Reactivate restaurant", responses={200: RestaurantSerializer})
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        try:
            restaurant = reactivate_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Close restaurant", responses={200: RestaurantSerializer})
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        try:
            restaurant = close_restaurant(uuid.UUID(pk))
            return Response(self.get_serializer(restaurant).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Check restaurant open status against business hours & holidays", responses={200: dict})
    @action(detail=True, methods=["get"], url_path="open-status")
    def open_status(self, request, pk=None):
        restaurant = self.get_object()
        is_open, reason = check_restaurant_open_status(uuid.UUID(str(restaurant.tenant_id)), timezone.now())
        return Response({"is_open": is_open, "reason": reason, "timestamp": timezone.now().isoformat()})


@extend_schema_view(
    list=extend_schema(summary="List dining tables"),
    create=extend_schema(summary="Create dining table"),
    retrieve=extend_schema(summary="Get dining table details"),
    update=extend_schema(summary="Update dining table"),
    partial_update=extend_schema(summary="Partially update dining table"),
    destroy=extend_schema(summary="Delete dining table"),
)
class DiningTableViewSet(BaseModelViewSet):
    serializer_class = DiningTableSerializer

    def get_queryset(self):
        return DiningTable.objects.all()

    @extend_schema(summary="Seat guests at table", responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"])
    def seat(self, request, pk=None):
        try:
            table = seat_guests(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Reserve table", responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"])
    def reserve(self, request, pk=None):
        try:
            table = reserve_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Release table back to vacant", responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        try:
            table = release_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Block table for maintenance/cleanup", responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        try:
            table = block_table(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Merge secondary tables into primary", request=MergeTablesInputSerializer, responses={200: DiningTableSerializer})
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

    @extend_schema(summary="Split merged tables back to vacant", responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"])
    def split(self, request, pk=None):
        try:
            table = split_tables(uuid.UUID(pk))
            return Response(self.get_serializer(table).data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Generate table QR ordering code", responses={200: dict})
    @action(detail=True, methods=["post"], url_path="generate-qr")
    def generate_qr(self, request, pk=None):
        try:
            qr_url = generate_table_qr_url(uuid.UUID(pk))
            return Response({"qr_code_url": qr_url})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Move table occupancy & active orders to target table", request=MoveTableInputSerializer, responses={200: DiningTableSerializer})
    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        serializer = MoveTableInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_table_id = serializer.validated_data["target_table_id"]
        source_table = self.get_object()

        try:
            target_table = DiningTable.objects.get(id=target_table_id, is_deleted=False)
        except DiningTable.DoesNotExist:
            return Response({"detail": "Target table not found."}, status=status.HTTP_404_NOT_FOUND)

        if str(target_table.id) == str(source_table.id):
            return Response({"detail": "Cannot move a table to itself."}, status=status.HTTP_400_BAD_REQUEST)

        if target_table.status != TableStatus.VACANT:
            return Response({"detail": "Target table is not vacant."}, status=status.HTTP_400_BAD_REQUEST)

        from contexts.ordering.models.order import Order
        from contexts.ordering.domain.enums import OrderStatus

        with transaction.atomic():
            Order.objects.filter(table_id=source_table.id, status=OrderStatus.OPEN).update(table_id=target_table.id)
            if source_table.status in (TableStatus.OCCUPIED, TableStatus.RESERVED):
                release_table(source_table.id)
                seat_guests(target_table.id)

        target_table.refresh_from_db()
        return Response(self.get_serializer(target_table).data, status=status.HTTP_200_OK)

    @extend_schema(summary="Get table status summary and occupancy metrics", responses={200: dict})
    @action(detail=False, methods=["get"], url_path="status")
    def status_summary(self, request):
        tables = self.get_queryset().filter(is_active=True, is_deleted=False)
        total = tables.count()
        status_counts = {}
        for st_val, _ in TableStatus.choices:
            status_counts[st_val] = tables.filter(status=st_val).count()
        occupied = status_counts.get(TableStatus.OCCUPIED, 0)
        occupancy_rate = int((occupied / total) * 100) if total > 0 else 0
        return Response({
            "total_tables": total,
            "occupancy_rate": occupancy_rate,
            "status_counts": status_counts,
        })

    @extend_schema(summary="Get vacant tables available for seating", responses={200: DiningTableSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        qs = self.get_queryset().filter(status=TableStatus.VACANT, is_active=True, is_deleted=False)
        min_capacity = request.query_params.get("min_capacity")
        if min_capacity and str(min_capacity).isdigit():
            qs = qs.filter(capacity__gte=int(min_capacity))
        return Response(self.get_serializer(qs.order_by("number"), many=True).data)

    @extend_schema(summary="Get or update physical floor layout table positions", request=FloorLayoutBatchUpdateSerializer, responses={200: DiningTableSerializer(many=True)})
    @action(detail=False, methods=["get", "post"], url_path="layout")
    def layout(self, request):
        if request.method.lower() == "post":
            serializer = FloorLayoutBatchUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                for item in serializer.validated_data["tables"]:
                    t_id = item["table_id"]
                    fields_to_upd = {"position_x": item["position_x"], "position_y": item["position_y"]}
                    if "rotation" in item:
                        fields_to_upd["rotation"] = item["rotation"]
                    if "shape" in item:
                        fields_to_upd["shape"] = item["shape"]
                    DiningTable.objects.filter(id=t_id, is_deleted=False).update(**fields_to_upd)
        qs = self.get_queryset().filter(is_active=True, is_deleted=False).order_by("number")
        return Response(self.get_serializer(qs, many=True).data)


@extend_schema_view(
    list=extend_schema(summary="List kitchen stations"),
    create=extend_schema(summary="Create kitchen station"),
    retrieve=extend_schema(summary="Get kitchen station details"),
    update=extend_schema(summary="Update kitchen station"),
    partial_update=extend_schema(summary="Partially update station"),
    destroy=extend_schema(summary="Delete kitchen station"),
)
class KitchenStationViewSet(BaseModelViewSet):
    serializer_class = KitchenStationSerializer

    def get_queryset(self):
        return KitchenStation.objects.all()


@extend_schema_view(
    list=extend_schema(summary="List printers"),
    create=extend_schema(summary="Create printer configuration"),
    retrieve=extend_schema(summary="Get printer configuration"),
    update=extend_schema(summary="Update printer configuration"),
    partial_update=extend_schema(summary="Partially update printer"),
    destroy=extend_schema(summary="Delete printer"),
)
class PrinterViewSet(BaseModelViewSet):
    serializer_class = PrinterSerializer

    def get_queryset(self):
        return Printer.objects.all()

    @extend_schema(summary="Execute simulated diagnostic test print", responses={200: dict})
    @action(detail=True, methods=["post"], url_path="test-print")
    def test_print(self, request, pk=None):
        printer = self.get_object()
        conn_info = printer.connection or {}
        payload = {
            "printer_name": printer.name,
            "code": printer.code,
            "kind": printer.kind,
            "connection": conn_info,
            "timestamp": timezone.now().isoformat(),
            "status": "ONLINE - SUCCESS",
            "test_lines": [
                "NEXTORA POS - SYSTEM DIAGNOSTIC",
                "===============================",
                f"PRINTER TYPE: {printer.kind.upper()}",
                "STATUS: ONLINE - SUCCESS",
                "Simulated Test Print Complete.",
            ],
        }
        return Response(payload, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List cash counters"),
    create=extend_schema(summary="Create cash counter"),
    retrieve=extend_schema(summary="Get cash counter"),
    update=extend_schema(summary="Update cash counter"),
    partial_update=extend_schema(summary="Partially update cash counter"),
    destroy=extend_schema(summary="Delete cash counter"),
)
class CashCounterViewSet(BaseModelViewSet):
    serializer_class = CashCounterSerializer

    def get_queryset(self):
        return CashCounter.objects.all()


@extend_schema_view(
    list=extend_schema(summary="List holiday overrides"),
    create=extend_schema(summary="Create holiday override"),
    retrieve=extend_schema(summary="Get holiday details"),
    update=extend_schema(summary="Update holiday override"),
    partial_update=extend_schema(summary="Partially update holiday override"),
    destroy=extend_schema(summary="Delete holiday override"),
)
class HolidayViewSet(BaseModelViewSet):
    serializer_class = HolidaySerializer

    def get_queryset(self):
        return Holiday.objects.all()


@extend_schema_view(
    list=extend_schema(summary="List weekly business hours"),
    create=extend_schema(summary="Create business hours entry"),
    retrieve=extend_schema(summary="Get business hours entry details"),
    update=extend_schema(summary="Update business hours entry"),
    partial_update=extend_schema(summary="Partially update business hours entry"),
    destroy=extend_schema(summary="Delete business hours entry"),
)
class BusinessHoursViewSet(BaseModelViewSet):
    serializer_class = BusinessHoursSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BusinessHours.objects.all().order_by("day_of_week")

    @extend_schema(summary="Configure operating hours for a specific day of week", request=BusinessHoursInputSerializer, responses={200: BusinessHoursSerializer})
    @action(detail=False, methods=["post"], url_path="configure")
    def configure(self, request):
        serializer = BusinessHoursInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from shared.tenancy.context import get_current_tenant
        tenant_id = request.META.get("HTTP_X_TENANT_ID") or getattr(request, "tenant_id", None) or get_current_tenant()
        if not tenant_id:
            return Response({"detail": "Tenant identification missing."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            hours = set_business_hours(
                tenant_id=uuid.UUID(str(tenant_id)),
                day_of_week=serializer.validated_data["day_of_week"],
                open_time=serializer.validated_data["open_time"],
                close_time=serializer.validated_data["close_time"],
                is_closed=serializer.validated_data.get("is_closed", False),
            )
            return Response(self.get_serializer(hours).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Check current operating status against business hours and holidays", responses={200: dict})
    @action(detail=False, methods=["get"], url_path="current-status")
    def current_status(self, request):
        from shared.tenancy.context import get_current_tenant
        tenant_id = request.META.get("HTTP_X_TENANT_ID") or getattr(request, "tenant_id", None) or get_current_tenant()
        if not tenant_id:
            return Response({"detail": "Tenant identification missing."}, status=status.HTTP_400_BAD_REQUEST)
        is_open, reason = check_restaurant_open_status(uuid.UUID(str(tenant_id)), timezone.now())
        return Response({
            "is_open": is_open,
            "reason": reason,
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
