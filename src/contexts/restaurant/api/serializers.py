from rest_framework import serializers

from ..domain.enums import GSTRegistrationType

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


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "id", "name", "slug", "description", "status", "logo",
            "address_line1", "address_line2", "city", "state", "pincode", "country",
            "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "status", "is_default", "created_at", "updated_at"]


class BranchGSTProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchGSTProfile
        fields = [
            "id", "gstin", "legal_name", "state_code", "registration_type", "pan", "is_active"
        ]
        read_only_fields = ["id", "state_code", "pan"]


class BranchSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchSettings
        fields = [
            "id", "invoice_prefix", "invoice_footer", "auto_accept_orders",
            "default_order_type", "enable_customer_self_ordering", "table_layout_mode",
            "notification_settings", "theme"
        ]
        read_only_fields = ["id"]


class BranchSerializer(serializers.ModelSerializer):
    gst_profile = BranchGSTProfileSerializer(read_only=True)
    settings = BranchSettingsSerializer(read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id", "restaurant", "name", "code", "status", "address_line1",
            "address_line2", "city", "state", "pincode", "country",
            "latitude", "longitude", "phone", "email", "service_modes",
            "timezone", "currency", "is_active", "gst_profile", "settings",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class DiningTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiningTable
        fields = [
            "id", "branch", "number", "capacity", "status", "assigned_waiter_id",
            "shape", "merge_group", "position_x", "position_y", "rotation",
            "qr_code_url", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "qr_code_url"]


class KitchenStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenStation
        fields = ["id", "branch", "code", "name", "kind", "sort_order", "is_active"]
        read_only_fields = ["id"]


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = ["id", "branch", "code", "name", "kind", "connection", "station", "is_active"]
        read_only_fields = ["id"]


class CashCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashCounter
        fields = ["id", "branch", "name", "code", "is_active"]
        read_only_fields = ["id"]


class BusinessHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHours
        fields = ["id", "branch", "day_of_week", "open_time", "close_time", "is_closed"]
        read_only_fields = ["id"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "branch", "date", "name", "is_full_day", "open_time", "close_time"]
        read_only_fields = ["id"]


# Custom action input serializers
class SeatingSerializer(serializers.Serializer):
    pass


class MergeTablesInputSerializer(serializers.Serializer):
    secondary_table_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )


class BusinessHoursInputSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=1, max_value=7)
    open_time = serializers.TimeField()
    close_time = serializers.TimeField()
    is_closed = serializers.BooleanField(required=False, default=False)


class GSTProfileInputSerializer(serializers.Serializer):
    gstin = serializers.CharField(max_length=15)
    legal_name = serializers.CharField(max_length=255)
    registration_type = serializers.ChoiceField(
        choices=GSTRegistrationType.choices, default=GSTRegistrationType.REGULAR
    )
