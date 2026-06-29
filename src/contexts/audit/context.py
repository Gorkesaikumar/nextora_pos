"""Request-scoped actor context for audit logging.

Captures WHO is acting and from WHERE, so the audit writer doesn't need the
request object passed down through every layer.
"""
import uuid
from contextvars import ContextVar

_actor_id: ContextVar[uuid.UUID | None] = ContextVar("audit_actor_id", default=None)
_ip_address: ContextVar[str | None] = ContextVar("audit_ip", default=None)
_device: ContextVar[str | None] = ContextVar("audit_device", default=None)
_browser: ContextVar[str | None] = ContextVar("audit_browser", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("audit_correlation_id", default=None)


def set_actor(
    actor_id: uuid.UUID | None, 
    ip_address: str | None,
    device: str | None = None,
    browser: str | None = None,
    correlation_id: str | None = None,
) -> None:
    _actor_id.set(actor_id)
    _ip_address.set(ip_address)
    _device.set(device)
    _browser.set(browser)
    _correlation_id.set(correlation_id)


def get_actor_id() -> uuid.UUID | None:
    return _actor_id.get()


def get_ip_address() -> str | None:
    return _ip_address.get()


def get_device() -> str | None:
    return _device.get()


def get_browser() -> str | None:
    return _browser.get()


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def clear_actor() -> None:
    _actor_id.set(None)
    _ip_address.set(None)
    _device.set(None)
    _browser.set(None)
    _correlation_id.set(None)
