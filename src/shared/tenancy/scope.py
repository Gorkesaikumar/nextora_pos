"""tenant_scope — bind a tenant for both the app layer and the DB session.

Use in Celery tasks and services that may run outside a request: it sets the
contextvar (so TenantManager filters correctly) AND the Postgres GUC (so RLS
permits the rows), then restores the previous scope on exit.
"""
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from django.conf import settings

from .context import get_current_tenant, set_current_tenant
from .db import clear_db_tenant, set_db_tenant


@contextmanager
def tenant_scope(tenant_id: uuid.UUID) -> Iterator[None]:
    previous = get_current_tenant()
    local = getattr(settings, "TENANCY_DB_LOCAL_GUC", False)

    set_current_tenant(tenant_id)
    set_db_tenant(tenant_id, local=local)
    try:
        yield
    finally:
        set_current_tenant(previous)
        if previous is None:
            clear_db_tenant(local=local)
        else:
            set_db_tenant(previous, local=local)
