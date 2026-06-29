"""Database router for future tenant sharding.

Today every tenant lives on the ``default`` database. This router is the seam
that lets us later move heavy tenants to dedicated shards WITHOUT changing data
shape or application code:

    settings.TENANCY_SHARD_MAP = {
        "<tenant-uuid>": "shard_01",
        "<tenant-uuid>": "shard_02",
    }   # everything else -> "default"

Because every table already carries tenant_id and we have logical per-tenant
export/import, sharding a tenant is an operational task (export -> import ->
update map), not a migration.
"""
from typing import Any

from django.conf import settings

from .context import get_current_tenant

_DEFAULT_ALIAS = "default"


def _shard_for_current_tenant() -> str:
    tenant_id = get_current_tenant()
    if tenant_id is None:
        return _DEFAULT_ALIAS
    shard_map: dict[str, str] = getattr(settings, "TENANCY_SHARD_MAP", {})
    return shard_map.get(str(tenant_id), _DEFAULT_ALIAS)


class TenantShardRouter:
    def db_for_read(self, model: Any, **hints: Any) -> str:
        return _shard_for_current_tenant()

    def db_for_write(self, model: Any, **hints: Any) -> str:
        return _shard_for_current_tenant()

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool | None:
        # Relations are allowed within the same shard; cross-shard relations
        # never occur because a tenant lives entirely on one shard.
        return None

    def allow_migrate(self, db: str, app_label: str, **hints: Any) -> bool | None:
        # Schema is identical on every shard; migrate everywhere.
        return True
