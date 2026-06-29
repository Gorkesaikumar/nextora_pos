"""Tenant resolution middleware (Layer 1).

For each request it:
  1. Resolves the tenant from the host (white-label domain or slug subdomain).
  2. Rejects unknown hosts (404) and inactive tenants (403) — fail closed.
  3. Binds the tenant to the app context (Layer 2/3) and the DB session GUC
     (Layer 4 / RLS), and mirrors it into the logging context for correlation.
  4. ALWAYS clears the context and DB GUC afterwards (finally), so a pooled
     connection / reused thread never leaks one tenant's scope into the next.

Health/admin/static paths are exempt (they are tenant-agnostic infrastructure).
"""
import logging
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse

from shared.infrastructure.logging.context import set_tenant_id as set_log_tenant

from .context import clear_current_tenant, set_current_tenant
from .db import clear_db_tenant, set_db_tenant
from .resolver import ResolvedTenant, resolve_from_host

logger = logging.getLogger("nextora.tenancy")

_EXEMPT_PREFIXES = (
    "/healthz/", "/admin/", "/static/", "/media/", "/__debug__/", "/webhooks/",
)
_INACTIVE_STATUSES = {"suspended", "churned"}


class TenantResolutionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.local_guc = getattr(settings, "TENANCY_DB_LOCAL_GUC", False)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith(_EXEMPT_PREFIXES):
            return self.get_response(request)

        resolved = resolve_from_host(request.get_host())
        if resolved is None:
            # Fallback 1: explicit X-Tenant-ID header (API / internal clients).
            resolved = self._resolve_from_header(request)
        if resolved is None:
            # Fallback 2: a session-authenticated user with exactly one tenant
            # membership (covers central-domain / non-subdomain access).
            resolved = self._resolve_from_user(request)
        if resolved is None and settings.DEBUG and request.get_host().split(":")[0] in ("127.0.0.1", "localhost"):
            # Fallback 3 (Dev only): auto-resolve to the first active tenant.
            resolved = self._resolve_first_tenant_for_dev()
        if resolved is None:
            logger.warning("Unknown tenant host: %s", request.get_host())
            return JsonResponse({"detail": "Unknown tenant."}, status=404)

        if resolved.status in _INACTIVE_STATUSES:
            return HttpResponseForbidden("Tenant is not active.")

        # Bind all layers.
        set_current_tenant(resolved.tenant_id)
        set_log_tenant(str(resolved.tenant_id))
        set_db_tenant(resolved.tenant_id, local=self.local_guc)
        request.tenant_id = resolved.tenant_id  # type: ignore[attr-defined]

        try:
            return self.get_response(request)
        finally:
            clear_current_tenant()
            clear_db_tenant(local=self.local_guc)
            set_log_tenant("-")  # don't leak this tenant into later log lines

    @staticmethod
    def _resolve_from_header(request: HttpRequest) -> ResolvedTenant | None:
        """Resolve from X-Tenant-ID header (JWT API clients, test harness)."""
        import uuid as _uuid
        header_val = request.META.get("HTTP_X_TENANT_ID")
        if not header_val:
            return None
        try:
            tenant_id = _uuid.UUID(header_val)
        except ValueError:
            return None
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        with bypass_tenant():
            tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return None
        return ResolvedTenant(tenant.id, tenant.status)

    @staticmethod
    def _resolve_from_user(request: HttpRequest) -> ResolvedTenant | None:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        # Imported lazily to avoid an app-loading import cycle.
        from contexts.identity.models import Membership
        from shared.tenancy.context import bypass_tenant

        # Must bypass tenant context — no tenant is bound yet at this point,
        # so TenantSoftDeleteManager would return qs.none() (fail-closed).
        with bypass_tenant():
            memberships = list(
                Membership.objects.filter(
                    user=user, is_active=True, tenant__isnull=False
                ).select_related("tenant")
            )

        if not memberships:
            return None

        # Drop memberships to suspended/churned tenants so the middleware
        # never resolves to a tenant the user shouldn't access.
        memberships = [
            m for m in memberships if m.tenant.status not in _INACTIVE_STATUSES
        ]
        if not memberships:
            return None

        # Honor the workspace the user explicitly picked (set by the tenant
        # picker in the session), but ONLY if they genuinely belong to it — a
        # tampered session must never grant cross-tenant access. For users with
        # several memberships this is what makes the picker's choice stick;
        # without it the middleware always fell back to the first membership.
        chosen = request.session.get("active_tenant_id")
        membership = None
        if chosen:
            membership = next(
                (m for m in memberships if str(m.tenant_id) == str(chosen)), None
            )
        if membership is None:
            membership = memberships[0]

        return ResolvedTenant(membership.tenant_id, membership.tenant.status)

    @staticmethod
    def _resolve_first_tenant_for_dev() -> ResolvedTenant | None:
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant

        with bypass_tenant():
            tenant = Tenant.objects.filter(status="active").first()
        if tenant is None:
            return None
        return ResolvedTenant(tenant.id, tenant.status)
