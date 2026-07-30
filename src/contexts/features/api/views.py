from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache

from contexts.features.api.serializers import (
    BulkEvaluateRequestSerializer,
    FeatureValidationRequestSerializer,
    FeatureCacheClearSerializer,
)
from contexts.features.services import bulk_evaluate, evaluate_flag, _get_flag_cache_key
from shared.tenancy.context import get_current_tenant
from shared.api.views import BaseAPIView
from contexts.billing.models import Subscription
from contexts.billing.domain.enums import SubscriptionStatus


class FeatureEvaluationView(BaseAPIView):
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


class SubscriptionFeaturesView(BaseAPIView):
    """Retrieve the core features enabled by the active subscription."""
    @extend_schema(responses={200: dict})
    def get(self, request, *args, **kwargs):
        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response({"detail": "Tenant required."}, status=status.HTTP_400_BAD_REQUEST)
        
        subscription = Subscription.objects.filter(
            tenant_id=tenant_id, 
            status__in=SubscriptionStatus.occupied(), 
            is_deleted=False
        ).select_related("plan").first()
        
        features = {}
        if subscription and subscription.plan and subscription.plan.features:
            features = subscription.plan.features
            
        return Response({
            "all_pos_features": True,
            "add_ons": features,
        }, status=status.HTTP_200_OK)


class EnabledModulesView(BaseAPIView):
    """Retrieve the globally enabled core modules for the application."""
    tenant_agnostic = True
    
    @extend_schema(responses={200: dict})
    def get(self, request, *args, **kwargs):
        modules = {
            "ordering": True,
            "catalog": True,
            "inventory": True,
            "identity": True,
            "reporting": True,
            "tenants": True,
            "billing": True,
        }
        return Response(modules, status=status.HTTP_200_OK)


class FeatureLimitsView(BaseAPIView):
    """Retrieve usage limits applied to the current tenant."""
    @extend_schema(responses={200: dict})
    def get(self, request, *args, **kwargs):
        limits = {
            "max_users": -1,
            "max_branches": -1,
            "max_products": -1,
            "max_orders_per_month": -1,
        }
        return Response(limits, status=status.HTTP_200_OK)


class FeatureValidationView(BaseAPIView):
    """Explicitly validate a single feature flag and retrieve detailed reason."""
    @extend_schema(
        request=FeatureValidationRequestSerializer,
        responses={200: dict},
    )
    def post(self, request, *args, **kwargs):
        serializer = FeatureValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        key = serializer.validated_data["key"]
        client_context = serializer.validated_data.get("context", {})
        tenant_id = get_current_tenant()
        
        evaluation_context = {
            **client_context,
            "tenant_id": str(tenant_id) if tenant_id else None,
        }
        
        if key == "all_pos_features":
            return Response({"allowed": True, "reason": "core_feature"}, status=status.HTTP_200_OK)
            
        allowed = evaluate_flag(key, evaluation_context)
        return Response({
            "allowed": allowed, 
            "reason": "evaluated_flag" if allowed else "flag_disabled_or_unmet_rules"
        }, status=status.HTTP_200_OK)


class FeatureCacheClearView(BaseAPIView):
    """Clear Redis cache for evaluated feature flags."""
    tenant_agnostic = True
    
    @extend_schema(
        request=FeatureCacheClearSerializer,
        responses={200: dict},
    )
    def post(self, request, *args, **kwargs):
        serializer = FeatureCacheClearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        keys = serializer.validated_data.get("keys", [])
        if keys:
            for key in keys:
                cache.delete(_get_flag_cache_key(key))
            msg = f"Cleared cache for {len(keys)} flags."
        else:
            cache.clear()
            msg = "Cleared all cache."
            
        return Response({"detail": msg}, status=status.HTTP_200_OK)
