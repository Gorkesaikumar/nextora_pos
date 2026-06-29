"""Tenant-aware base model (Layers 2 & 3).

Every tenant-owned table extends TenantAwareModel instead of BaseModel. It adds:
  * a non-null ``tenant`` FK (PROTECT — a tenant's rows are never implicitly
    cascade-deleted),
  * tenant-aware managers (automatic filtering),
  * a save() write-guard that auto-stamps the tenant and rejects cross-tenant
    writes (CrossTenantAccess).

The FK is declared as a string reference ("tenants.Tenant") so the shared
kernel does not import the tenants context (no dependency cycle).
"""
import uuid

from django.db import models

from shared.infrastructure.models.base import BaseModel

from .context import get_current_tenant, is_bypass
from .exceptions import CrossTenantAccess, TenantNotResolved
from .managers import TenantSoftDeleteManager, TenantUnscopedManager


class TenantAwareModel(BaseModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="+",          # no reverse accessor; keeps Tenant clean
        db_index=True,
        editable=False,
    )

    # Order matters: the first manager is the default (_default_manager).
    objects = TenantSoftDeleteManager()
    all_objects = TenantUnscopedManager()

    class Meta(BaseModel.Meta):
        abstract = True

    def save(self, *args, **kwargs):  # type: ignore[override]
        current = get_current_tenant()

        if self.tenant_id is None:
            # New row: stamp the tenant from context.
            if current is None:
                raise TenantNotResolved(
                    f"Cannot save {type(self).__name__} without a tenant in "
                    f"context."
                )
            self.tenant_id = current
        elif current is not None and not is_bypass():
            # Existing/explicit tenant: it MUST match the active tenant.
            if _as_uuid(self.tenant_id) != _as_uuid(current):
                raise CrossTenantAccess(
                    f"Refusing to write {type(self).__name__} for tenant "
                    f"{self.tenant_id} while current tenant is {current}."
                )

        super().save(*args, **kwargs)


def _as_uuid(value: uuid.UUID | str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
