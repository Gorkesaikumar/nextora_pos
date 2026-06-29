"""Tenant-aware managers (Layer 2: automatic filtering).

TenantManager rewrites the default queryset to ``filter(tenant_id=current)``
so application code is tenant-safe by default and developers cannot forget to
scope a query.

Fail-closed policy: if there is no tenant in context and we are not explicitly
bypassing, the queryset is EMPTY (``none()``) and a warning is logged. A missing
scope must never fall through to "all tenants".

Manager variants
----------------
* TenantManager           — tenant filter only (for append-only models like
                            audit_log that have no soft-delete column).
* TenantSoftDeleteManager — tenant filter + ``is_deleted = false`` (the default
                            for TenantAwareModel).
* TenantUnscopedManager   — no tenant filter, sees deleted rows too. The
                            explicit escape hatch (admin, migrations, system).
                            Still subject to DB RLS unless the connection role
                            has BYPASSRLS.
"""
import logging

from django.db import models

from .context import get_current_tenant, is_bypass

logger = logging.getLogger("nextora.tenancy")


class TenantManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        qs = super().get_queryset()
        if is_bypass():
            return qs
        tenant_id = get_current_tenant()
        if tenant_id is None:
            logger.warning(
                "Tenant-scoped query with no tenant in context; returning "
                "empty result (fail-closed).",
                extra={"model": self.model.__name__},
            )
            return qs.none()
        return qs.filter(tenant_id=tenant_id)


class TenantSoftDeleteManager(TenantManager):
    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(is_deleted=False)


class TenantUnscopedManager(models.Manager):
    """Sees every tenant and every (incl. soft-deleted) row. Use deliberately."""
