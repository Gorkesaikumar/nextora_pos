"""Catalog API.

Reads require `catalog.view`; writes and bulk operations require `catalog.manage`.
Querysets are tenant-scoped automatically by the manager (RLS backs it at the
DB). Permission classes are resolved per-action.
"""
from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contexts.catalog.api.serializers import ProductSerializer
from contexts.catalog.models import Product
from contexts.catalog.services.import_export import (
    import_products_csv,
    stream_products_csv,
)
from contexts.identity.api.permissions import RequirePermission


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return (
            Product.objects.select_related("category", "tax_class")
            .prefetch_related("variants")
            .all()
        )

    def get_permissions(self):
        read_only = self.action in {"list", "retrieve", "export"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), RequirePermission(code)()]

    @action(detail=False, methods=["get"])
    def export(self, request):
        # Streamed so a large catalog never materialises fully in memory.
        response = StreamingHttpResponse(
            stream_products_csv(self.get_queryset()), content_type="text/csv"
        )
        response["Content-Disposition"] = 'attachment; filename="products.csv"'
        return response

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def import_csv(self, request):
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


from contexts.catalog.api.serializers import ModifierGroupSerializer, ModifierSerializer
from contexts.catalog.models import ModifierGroup, Modifier


class ModifierGroupViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierGroupSerializer

    def get_queryset(self):
        qs = ModifierGroup.objects.prefetch_related("modifiers").all()
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_permissions(self):
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), RequirePermission(code)()]


class ModifierViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierSerializer

    def get_queryset(self):
        qs = Modifier.objects.select_related("group").all()
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def get_permissions(self):
        read_only = self.action in {"list", "retrieve"}
        code = "catalog.view" if read_only else "catalog.manage"
        return [IsAuthenticated(), RequirePermission(code)()]

