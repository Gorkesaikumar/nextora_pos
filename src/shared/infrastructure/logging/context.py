"""Request-scoped logging context.

Uses contextvars so the same correlation data (request_id, tenant_id) is
available to:
  * synchronous request handling,
  * Celery tasks (copied across the boundary),
  * management commands.

This is what makes a single log query able to follow one user action from the
HTTP request through every async side effect.
"""
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="-")


def set_request_id(value: str) -> None:
    request_id_var.set(value)


def get_request_id() -> str:
    return request_id_var.get()


def set_tenant_id(value: str) -> None:
    tenant_id_var.set(value)


def get_tenant_id() -> str:
    return tenant_id_var.get()
