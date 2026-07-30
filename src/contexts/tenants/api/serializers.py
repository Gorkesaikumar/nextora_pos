from rest_framework import serializers

from shared.api.serializers import BaseModelSerializer
from contexts.tenants.models import Tenant, TenantConfiguration


class TenantSerializer(BaseModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id",
            "slug",
            "name",
            "legal_name",
            "category",
            "status",
            "country",
            "base_currency",
            "timezone",
            "created_at",
            "updated_at",
        ]


class TenantConfigurationSerializer(BaseModelSerializer):
    logo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = TenantConfiguration
        fields = [
            "id",
            "gst_number",
            "currency",
            "timezone",
            "invoice_prefix",
            "invoice_footer",
            "printer_settings",
            "kitchen_settings",
            "discount_rules",
            "tax_rules",
            "notification_settings",
            "business_hours",
            "working_days",
            "theme",
            "logo",
            "language",
            "created_at",
            "updated_at",
        ]
