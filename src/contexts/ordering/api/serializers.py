from rest_framework import serializers

from contexts.ordering.models import Order, OrderItem, Payment


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "product_id", "variant_id", "name_snapshot", "qty",
            "unit_price", "modifiers_total", "line_discount", "tax_rate",
            "cess_rate", "hsn_code", "kitchen_station_id", "line_subtotal",
            "line_total", "status", "notes",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "kind", "method", "amount", "tendered", "change_due",
            "reference", "status", "refund_reason", "captured_at",
            "created_by",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "location_id", "order_number", "table_id", "type",
            "status", "customer_name", "customer_phone", "currency",
            "is_interstate", "discount_type", "discount_value",
            "service_charge_rate", "subtotal", "discount_amount",
            "service_charge_amount", "taxable_amount", "cgst", "sgst",
            "igst", "cess", "tax_amount", "round_off", "total",
            "paid_amount", "due_amount", "opened_at", "settled_at",
            "voided_at", "void_reason", "created_by", "items", "payments",
        ]
        read_only_fields = [
            "id", "order_number", "status", "subtotal", "discount_amount",
            "service_charge_amount", "taxable_amount", "cgst", "sgst",
            "igst", "cess", "tax_amount", "round_off", "total",
            "paid_amount", "due_amount", "opened_at", "settled_at",
            "voided_at", "void_reason",
        ]
