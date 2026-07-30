from rest_framework import serializers

from shared.api.serializers import BaseModelSerializer
from contexts.ordering.models import (
    Order,
    OrderItem,
    OrderItemModifier,
    Payment,
    KOT,
    KOTItem,
    PrintJob,
    Invoice,
)


class OrderItemModifierSerializer(BaseModelSerializer):
    class Meta:
        model = OrderItemModifier
        fields = [
            "id",
            "modifier_id",
            "name_snapshot",
            "price_delta",
            "qty",
        ]


class OrderItemSerializer(BaseModelSerializer):
    modifiers = OrderItemModifierSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "variant_id",
            "name_snapshot",
            "qty",
            "unit_price",
            "modifiers_total",
            "line_discount",
            "tax_rate",
            "cess_rate",
            "hsn_code",
            "kitchen_station_id",
            "line_subtotal",
            "line_total",
            "status",
            "notes",
            "modifiers",
            "combo_id",
        ]


class PaymentSerializer(BaseModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "kind",
            "method",
            "amount",
            "tendered",
            "change_due",
            "reference",
            "status",
            "refund_reason",
            "captured_at",
            "created_by",
        ]


class OrderSerializer(BaseModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    location_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    class Meta:
        model = Order
        fields = [
            "id",
            "location_id",
            "order_number",
            "table_id",
            "type",
            "status",
            "customer_name",
            "customer_phone",
            "currency",
            "is_interstate",
            "discount_type",
            "discount_value",
            "service_charge_rate",
            "subtotal",
            "discount_amount",
            "service_charge_amount",
            "taxable_amount",
            "cgst",
            "sgst",
            "igst",
            "cess",
            "tax_amount",
            "round_off",
            "total",
            "paid_amount",
            "due_amount",
            "opened_at",
            "settled_at",
            "voided_at",
            "void_reason",
            "created_by",
            "items",
            "payments",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "status",
            "subtotal",
            "discount_amount",
            "service_charge_amount",
            "taxable_amount",
            "cgst",
            "sgst",
            "igst",
            "cess",
            "tax_amount",
            "round_off",
            "total",
            "paid_amount",
            "due_amount",
            "opened_at",
            "settled_at",
            "voided_at",
            "void_reason",
        ]


class KOTItemSerializer(BaseModelSerializer):
    modifiers = serializers.SerializerMethodField()

    class Meta:
        model = KOTItem
        fields = [
            "id",
            "kot",
            "order_item",
            "name_snapshot",
            "qty",
            "notes",
            "is_completed",
            "modifiers",
        ]

    def get_modifiers(self, obj):
        if not obj.order_item:
            return []
        return [{"name": m.name_snapshot, "qty": m.qty} for m in obj.order_item.modifiers.all()]


class KOTSerializer(BaseModelSerializer):
    items = KOTItemSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    order_type = serializers.CharField(source="order.type", read_only=True)
    customer_name = serializers.CharField(source="order.customer_name", read_only=True)
    table_number = serializers.CharField(source="order.table_number", read_only=True)

    class Meta:
        model = KOT
        fields = [
            "id",
            "order",
            "order_number",
            "order_type",
            "customer_name",
            "table_number",
            "kitchen_station_id",
            "number",
            "status",
            "printed_at",
            "created_at_kot",
            "items",
        ]
        read_only_fields = ["id", "number", "created_at_kot", "order_number", "order_type", "customer_name", "table_number"]


class PrintJobSerializer(BaseModelSerializer):
    class Meta:
        model = PrintJob
        fields = [
            "id",
            "job_type",
            "status",
            "error_message",
            "printed_at",
            "retry_count",
            "created_at",
        ]


class InvoiceSerializer(BaseModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "order",
            "number",
            "series",
            "financial_year",
            "status",
            "subtotal",
            "discount_amount",
            "service_charge_amount",
            "taxable_amount",
            "cgst",
            "sgst",
            "igst",
            "cess",
            "tax_amount",
            "round_off",
            "total",
            "customer_name",
            "customer_phone",
            "issued_at",
            "voided_at",
            "void_reason",
        ]
