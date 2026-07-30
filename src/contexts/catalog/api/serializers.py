"""DRF serializers for the catalog API."""
from rest_framework import serializers

from contexts.catalog.models import (
    Category,
    ComboGroup,
    ComboGroupItem,
    ComboOffer,
    Modifier,
    ModifierGroup,
    PriceTier,
    Product,
    ProductVariant,
    TaxClass,
    Unit,
)
from shared.api.serializers import BaseModelSerializer


class CategorySerializer(BaseModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "parent",
            "name",
            "slug",
            "description",
            "sort_order",
            "is_active",
            "image_url",
            "station_id",
            "printer_id",
        ]


class TaxClassSerializer(BaseModelSerializer):
    class Meta:
        model = TaxClass
        fields = ["id", "name", "gst_rate", "cess_rate", "is_active"]


class ModifierSerializer(BaseModelSerializer):
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


class ModifierGroupSerializer(BaseModelSerializer):
    modifiers = ModifierSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = [
            "id",
            "name",
            "description",
            "selection_type",
            "min_select",
            "max_select",
            "is_required",
            "is_active",
            "sort_order",
            "modifiers",
        ]


class ProductVariantSerializer(BaseModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "name",
            "sku",
            "barcode",
            "price_delta",
            "is_default",
            "is_active",
            "sort_order",
        ]


class ProductSerializer(BaseModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    modifier_groups = ModifierGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "type",
            "sku",
            "barcode",
            "hsn_code",
            "tax_class",
            "base_price",
            "currency",
            "kitchen_station",
            "printer",
            "image",
            "track_inventory",
            "is_active",
            "sort_order",
            "variants",
            "modifier_groups",
        ]


class ComboGroupItemSerializer(BaseModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = ComboGroupItem
        fields = [
            "id",
            "group",
            "product",
            "product_name",
            "product_sku",
            "upgrade_surcharge",
            "sort_order",
        ]


class ComboGroupSerializer(BaseModelSerializer):
    items = ComboGroupItemSerializer(many=True, read_only=True)

    class Meta:
        model = ComboGroup
        fields = [
            "id",
            "combo",
            "name",
            "min_selections",
            "max_selections",
            "sort_order",
            "items",
        ]


class ComboOfferSerializer(BaseModelSerializer):
    groups = ComboGroupSerializer(many=True, read_only=True)

    class Meta:
        model = ComboOffer
        fields = [
            "id",
            "name",
            "internal_code",
            "description",
            "image",
            "status",
            "offer_type",
            "priority",
            "discount_value",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "available_days",
            "order_types",
            "min_order_value",
            "min_cart_items",
            "customer_eligibility",
            "eligibility_products",
            "eligibility_categories",
            "usage_limit_type",
            "usage_limit_value",
            "current_uses",
            "sort_order",
            "groups",
        ]


class PriceTierSerializer(BaseModelSerializer):
    class Meta:
        model = PriceTier
        fields = ["id", "name", "description", "is_active"]


class UnitSerializer(BaseModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "name", "abbreviation", "is_active"]
