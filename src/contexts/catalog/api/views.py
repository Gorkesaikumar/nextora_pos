"""Catalog API Views.

All views inherit from BaseModelViewSet to leverage global formatting, pagination,
filtering, and tenant-bound exception handling.
"""
from typing import Any

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contexts.catalog.api.serializers import (
    CategorySerializer,
    ComboOfferSerializer,
    ModifierGroupSerializer,
    ModifierSerializer,
    PriceTierSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    TaxClassSerializer,
    UnitSerializer,
)
from contexts.catalog.models import (
    Category,
    ComboOffer,
    Modifier,
    ModifierGroup,
    PriceTier,
    Product,
    ProductVariant,
    TaxClass,
    Unit,
)
from contexts.catalog.services.import_export import (
    import_products_csv,
    stream_products_csv,
)
from contexts.identity.api.permissions import RequirePermission
from shared.api.permissions import BasePermission
from shared.api.views import BaseModelViewSet


class CategoryViewSet(BaseModelViewSet):
    serializer_class = CategorySerializer
    filterset_fields = ["parent", "is_active"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["sort_order", "name"]

    def get_queryset(self) -> Any:
        return Category.objects.select_related("parent").all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class ProductVariantViewSet(BaseModelViewSet):
    serializer_class = ProductVariantSerializer
    filterset_fields = ["product", "is_default", "is_active"]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["sort_order", "name", "price_delta"]

    def get_queryset(self) -> Any:
        return ProductVariant.objects.select_related("product").all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class ProductViewSet(BaseModelViewSet):
    serializer_class = ProductSerializer
    filterset_fields = ["category", "type", "tax_class", "is_active"]
    search_fields = ["name", "sku", "barcode", "description"]
    ordering_fields = ["sort_order", "name", "base_price"]

    def get_queryset(self) -> Any:
        return (
            Product.objects.select_related("category", "tax_class")
            .prefetch_related("variants")
            .all()
        )

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve", "export"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]

    @action(detail=False, methods=["get"])
    def export(self, request: Any) -> StreamingHttpResponse:
        # Streamed so a large catalog never materialises fully in memory.
        response = StreamingHttpResponse(
            stream_products_csv(self.get_queryset()), content_type="text/csv"
        )
        response["Content-Disposition"] = 'attachment; filename="products.csv"'
        return response

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def import_csv(self, request: Any) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )
        text = upload.read().decode("utf-8")
        report = import_products_csv(text)
        return Response(
            {
                "created": report.created,
                "updated": report.updated,
                "errors": report.errors,
            },
            status=status.HTTP_200_OK if report.ok else status.HTTP_207_MULTI_STATUS,
        )


class ModifierGroupViewSet(BaseModelViewSet):
    serializer_class = ModifierGroupSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["sort_order", "name"]

    def get_queryset(self) -> Any:
        return ModifierGroup.objects.prefetch_related("modifiers").all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class ModifierViewSet(BaseModelViewSet):
    serializer_class = ModifierSerializer
    filterset_fields = ["is_default", "is_active"]
    search_fields = ["name", "sku"]
    ordering_fields = ["sort_order", "name", "price_delta"]

    def get_queryset(self) -> Any:
        qs = Modifier.objects.select_related("group").all()
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class ComboOfferViewSet(BaseModelViewSet):
    serializer_class = ComboOfferSerializer
    filterset_fields = ["status", "offer_type", "customer_eligibility"]
    search_fields = ["name", "internal_code"]
    ordering_fields = ["priority", "sort_order", "name"]

    def get_queryset(self) -> Any:
        return ComboOffer.objects.prefetch_related("groups__items__product").all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class PriceTierViewSet(BaseModelViewSet):
    serializer_class = PriceTierSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name"]

    def get_queryset(self) -> Any:
        return PriceTier.objects.all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class TaxClassViewSet(BaseModelViewSet):
    serializer_class = TaxClassSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "gst_rate"]

    def get_queryset(self) -> Any:
        return TaxClass.objects.all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class UnitViewSet(BaseModelViewSet):
    serializer_class = UnitSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "abbreviation"]
    ordering_fields = ["name"]

    def get_queryset(self) -> Any:
        return Unit.objects.all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]
