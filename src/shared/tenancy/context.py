"""Request-scoped tenant context.

The current tenant is stored in a contextvar so it propagates correctly across
synchronous calls, async views, and Celery tasks without thread-local hazards.

Two flags live here:
  * _current_tenant — the active tenant UUID (or None outside a tenant scope).
  * _bypass         — when True, the ORM tenant filter is skipped. ONLY trusted
                      system code (backups, cross-tenant beat jobs, restores)
                      may enable this, via the ``bypass_tenant`` context manager.

Nothing here imports Django — it is a pure, reusable primitive.
"""
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_current_tenant: ContextVar[uuid.UUID | None] = ContextVar(
    "current_tenant", default=None
)
_bypass: ContextVar[bool] = ContextVar("tenant_bypass", default=False)


def set_current_tenant(tenant_id: uuid.UUID | None) -> None:
    _current_tenant.set(tenant_id)


def get_current_tenant() -> uuid.UUID | None:
    return _current_tenant.get()


def clear_current_tenant() -> None:
    _current_tenant.set(None)


def is_bypass() -> bool:
    return _bypass.get()


@contextmanager
def tenant_context(tenant_id: uuid.UUID) -> Iterator[None]:
    """Run a block scoped to a specific tenant (e.g. a Celery task)."""
    token = _current_tenant.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant.reset(token)


@contextmanager
def bypass_tenant() -> Iterator[None]:
    """Run a block that may cross tenants. Use sparingly and audibly.

    Even under bypass, the DATABASE still enforces RLS unless the connection
    role has BYPASSRLS (nextora_admin). So bypass alone does not defeat
    isolation — it only relaxes the application-layer filter.
    """
    token = _bypass.set(True)
    try:
        yield
    finally:
        _bypass.reset(token)
