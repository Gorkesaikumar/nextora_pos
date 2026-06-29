from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.features.api.serializers import BulkEvaluateRequestSerializer
from contexts.features.services import bulk_evaluate
from shared.tenancy.context import get_current_tenant


class FeatureEvaluationView(APIView):
    """
    Evaluate feature flags for a given context.
    
    The tenant ID is automatically extracted from the authenticated session,
    but can be supplemented by passing a custom context dictionary.
    """

    @extend_schema(
        request=BulkEvaluateRequestSerializer,
        responses={200: dict},
    )
    def post(self, request, *args, **kwargs):
        serializer = BulkEvaluateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        keys = serializer.validated_data["keys"]
        client_context = serializer.validated_data.get("context", {})
        
        # Merge server-side guaranteed context (like tenant_id) with client overrides
        tenant_id = get_current_tenant()
        evaluation_context = {
            **client_context,
            "tenant_id": str(tenant_id) if tenant_id else None,
        }
        
        results = bulk_evaluate(keys, evaluation_context)
        return Response(results, status=status.HTTP_200_OK)
