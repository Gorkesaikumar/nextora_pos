import uuid
from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from contexts.tenants.api.serializers import TenantSerializer, TenantConfigurationSerializer
from contexts.tenants.models import Tenant, TenantConfiguration
from contexts.tenants.services import get_tenant_config, update_tenant_config
from shared.api.views import BaseModelViewSet
from shared.tenancy.context import get_current_tenant, bypass_tenant


class TenantViewSet(BaseModelViewSet):
    """
    API viewset for Tenant metadata, configurations, settings, features, and selection.
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    tenant_agnostic = True  # Allows workspace listing/switching without pre-existing resolved tenant headers
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        # Retrieve memberships for the authenticated user to locate authorized tenants
        from contexts.identity.models import Membership
        from shared.tenancy.context import bypass_tenant

        with bypass_tenant():
            memberships = list(
                Membership.objects.filter(
                    user=self.request.user,
                    is_active=True,
                    tenant__isnull=False
                ).select_related("tenant")
            )
            # Filter to active/trial tenants only
            tenant_ids = [m.tenant_id for m in memberships if m.tenant.is_active]
            return Tenant.objects.filter(id__in=tenant_ids)

    @action(detail=False, methods=["get"])
    def current(self, request) -> Response:
        """Retrieve metadata of the currently active/resolved tenant."""
        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "No tenant is currently selected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()
        if not tenant:
            return Response(
                {"detail": "Current tenant not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(tenant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def select(self, request) -> Response:
        """Switch the current active tenant session context."""
        tenant_id_str = request.data.get("tenant_id")
        if not tenant_id_str:
            return Response(
                {"detail": "tenant_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except ValueError:
            return Response(
                {"detail": "Invalid tenant_id format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Confirm user belongs to this tenant and it is active
        from contexts.identity.models import Membership
        from shared.tenancy.context import bypass_tenant
        with bypass_tenant():
            membership = Membership.objects.filter(
                user=request.user,
                tenant_id=tenant_id,
                is_active=True
            ).select_related("tenant").first()

        if not membership or not membership.tenant.is_active:
            return Response(
                {"detail": "Tenant not found or access denied."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Set active tenant in session for session-based request flows
        request.session["active_tenant_id"] = str(tenant_id)
        return Response(
            {
                "detail": "Tenant selected successfully.",
                "tenant_id": str(tenant_id)
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get", "patch"])
    def config(self, request) -> Response:
        """Retrieve or update configurations for the active tenant context."""
        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "No tenant is currently selected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == "GET":
            config_dict = get_tenant_config(tenant_id)
            return Response(config_dict, status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            serializer = TenantConfigurationSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            # Remove read-only attributes
            update_data = serializer.validated_data
            updated_config = update_tenant_config(tenant_id, **update_data)
            return Response(updated_config, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def features(self, request) -> Response:
        """List evaluated features available under the active tenant's subscription/country context."""
        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "No tenant is currently selected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from contexts.features.models import FeatureFlag
        from contexts.features.services import bulk_evaluate

        # Determine all feature flag keys registered in the system
        keys = list(FeatureFlag.objects.all().values_list("key", flat=True))

        evaluation_context = {
            "tenant_id": str(tenant_id),
        }

        # Retrieve tenant metadata and subscription details for rule evaluations
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant:
            evaluation_context["country"] = tenant.country

            # Locate active subscription plan
            from contexts.billing.models.subscription import Subscription
            from contexts.billing.domain.enums import SubscriptionStatus
            with bypass_tenant():
                sub = Subscription.objects.filter(
                    tenant_id=tenant_id,
                    status__in=SubscriptionStatus.occupied(),
                    is_deleted=False
                ).select_related("plan").first()
            if sub and sub.plan:
                evaluation_context["subscription_tier"] = sub.plan.code
            else:
                evaluation_context["subscription_tier"] = "trial"

        results = bulk_evaluate(keys, evaluation_context)
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="settings")
    def tenant_settings(self, request) -> Response:
        """Combine current tenant metadata and config dictionary for single-request initialization."""
        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "No tenant is currently selected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()
        if not tenant:
            return Response(
                {"detail": "Current tenant not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_data = self.get_serializer(tenant).data
        config_dict = get_tenant_config(tenant_id)
        tenant_data["config"] = config_dict
        return Response(tenant_data, status=status.HTTP_200_OK)
