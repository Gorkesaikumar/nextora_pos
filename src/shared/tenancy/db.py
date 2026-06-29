"""Database session binding for Row-Level Security (Layer 4).

RLS policies compare ``tenant_id`` against ``current_setting('app.current_tenant')``.
These helpers set/clear that GUC on the active connection.

Pooling note
------------
* Session pooling / direct connections: set at session scope (local=False).
* PgBouncer TRANSACTION pooling: the GUC must be set per-transaction, so use
  local=True together with ATOMIC_REQUESTS (or an explicit atomic block).
The choice is driven by settings.TENANCY_DB_LOCAL_GUC.
"""
import uuid

from django.db import connection


def set_db_tenant(tenant_id: uuid.UUID, *, local: bool) -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_tenant', %s, %s)",
            [str(tenant_id), local],
        )


def clear_db_tenant(*, local: bool) -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_tenant', '', %s)",
            [local],
        )
