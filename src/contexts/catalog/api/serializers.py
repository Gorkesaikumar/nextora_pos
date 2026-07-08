"""DRF serializers for the catalog API."""
from rest_framework import serializers

from contexts.catalog.models import (
    Category,
    Modifier,
    ModifierGroup,
    Product,
    ProductVariant,
    TaxClass,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "parent", "name", "description", "sort_order",
                  "is_active", "kitchen_station", "printer"]


class TaxClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxClass
        fields = ["id", "name", "gst_rate", "cess_rate", "is_active"]


class ModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modifier
        fields = [
            "id",
            "name",
            "sku",
            "price_delta",
            "inventory_item",
            "quantity_consumed",
            "is_default",
            "is_active",
            "sort_order",
        ]


class ModifierGroupSerializer(serializers.ModelSerializer):
    modifiers = ModifierSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "description",
            "min_select",
            "max_select",
            "is_required",
            "is_active",
            "sort_order",
            "modifiers",
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "name", "sku", "barcode", "price_delta",
                  "is_default", "is_active", "sort_order"]


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "category", "name", "description", "type",
            "sku", "barcode", "hsn_code", "tax_class",
            "base_price", "currency", "kitchen_station", "printer",
            "image", "track_inventory", "is_active", "sort_order", "variants",
            "modifier_groups",
        ]
        read_only_fields = ["id"]
