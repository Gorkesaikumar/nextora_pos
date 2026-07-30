"""Serializers for reporting and dashboard APIs."""
from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    sales_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_today = serializers.IntegerField()
    active_tables = serializers.IntegerField()
    average_ticket = serializers.DecimalField(max_digits=12, decimal_places=2)
    open_kots = serializers.IntegerField()
    refunds_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payments = serializers.DecimalField(max_digits=12, decimal_places=2)


class SalesMetricItemSerializer(serializers.Serializer):
    period = serializers.CharField()
    orders_count = serializers.IntegerField()
    gross_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=12, decimal_places=2)
    taxes = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=12, decimal_places=2)


class TopItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    qty_sold = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit = serializers.DecimalField(max_digits=12, decimal_places=2)


class TopCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    items_sold = serializers.DecimalField(max_digits=10, decimal_places=2)
    percentage = serializers.FloatField()


class PaymentMethodSummarySerializer(serializers.Serializer):
    method = serializers.CharField()
    transactions = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class GSTSummarySerializer(serializers.Serializer):
    hsn_summary = serializers.ListField(child=serializers.DictField())
    b2b_b2c_summary = serializers.DictField()


class SalesChartPointSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.FloatField()


class ProfitReportItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    margin_percentage = serializers.FloatField()


class StationUtilizationSerializer(serializers.Serializer):
    station_id = serializers.UUIDField()
    station_name = serializers.CharField()
    active_kots = serializers.IntegerField()


class KDSMetricsSerializer(serializers.Serializer):
    waiting = serializers.IntegerField()
    preparing = serializers.IntegerField()
    ready = serializers.IntegerField()
    delayed = serializers.IntegerField()
    avg_prep_time = serializers.CharField()
    completion_rate = serializers.IntegerField()
    orders_today = serializers.IntegerField()
    kitchen_efficiency = serializers.IntegerField()
    station_utilization = StationUtilizationSerializer(many=True)
