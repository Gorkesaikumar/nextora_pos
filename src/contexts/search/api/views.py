from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.tenancy.context import get_current_tenant
from .serializers import SearchQuerySerializer
from ..services import universal_search


class UniversalSearchView(APIView):
    """Search across multiple contexts (products, categories, invoices, etc.)

    with ranking, trigram fuzzy matching, and Redis caching.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[SearchQuerySerializer],
        responses={200: dict},
    )
    def get(self, request, *args, **kwargs):
        serializer = SearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["q"]
        entity_type = serializer.validated_data["type"]
        limit = serializer.validated_data["limit"]
        offset = serializer.validated_data["offset"]

        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "Tenant not resolved in current request context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = universal_search(
            query=query,
            tenant_id=tenant_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )
        return Response(results, status=status.HTTP_200_OK)
