"""Authorization enforcement points.

Usage (DRF viewset):
    class OrderViewSet(ViewSet):
        permission_classes = [IsAuthenticated, RequirePermission("orders.create")]

Usage (function / service):
    @require_permission("invoices.issue")
    def issue_invoice(...): ...

Both resolve the tenant from the request/tenancy context and an optional branch
from the request, then delegate to the DB-driven authorization service. The
permission CODE is the route's capability contract — not a role mapping.
"""
import functools
import uuid
from collections.abc import Callable
from typing import Any

from rest_framework.permissions import BasePermission

from contexts.identity.services.authorization import has_permission
from shared.tenancy.context import get_current_tenant
from shared.tenancy.exceptions import TenantNotResolved


def _request_location(request: Any) -> uuid.UUID | None:
    """Branch scope for the request, if any (header or query param)."""
    raw = (
        request.headers.get("X-Branch-ID")
        or request.query_params.get("location_id")
        if hasattr(request, "query_params")
        else request.headers.get("X-Branch-ID")
    )
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        return None


def RequirePermission(code: str) -> type[BasePermission]:  # noqa: N802 (factory)
    """Return a DRF permission class enforcing ``code``."""

    class _RequirePermission(BasePermission):
        message = f"Missing required permission: {code}"

        def has_permission(self, request: Any, view: Any) -> bool:
            return has_permission(
                request.user,
                code,
                get_current_tenant(),
                _request_location(request),
            )

    _RequirePermission.__name__ = f"RequirePermission[{code}]"
    return _RequirePermission


def require_permission(code: str) -> Callable:
    """Decorator for non-DRF callables. First arg must be the request.

    Raises PermissionError (or TenantNotResolved) when denied.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            tenant_id = get_current_tenant()
            if tenant_id is None:
                raise TenantNotResolved("No tenant in context for permission check.")
            if not has_permission(
                request.user, code, tenant_id, _request_location(request)
            ):
                raise PermissionError(f"Missing required permission: {code}")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
