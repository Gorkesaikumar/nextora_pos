"""Real-time broadcast helpers.

Pushes a small signal to every screen subscribed to a tenant's events
group. The signal carries no board markup — each client reacts by re-fetching the
permission-checked board partial over HTTP — so this is cheap and leaks nothing.

Best-effort by design: a channel-layer hiccup must never break the action
that triggered it, so failures are logged and swallowed.
"""
import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from contexts.ordering.consumers import tenant_group_name
from shared.tenancy.context import get_current_tenant

logger = logging.getLogger("nextora.realtime")


def broadcast_tenant_event(
    event_type: str,
    *,
    tenant_id: uuid.UUID | None = None,
    message: str | None = None,
    payload: dict | None = None,
) -> None:
    """Notify all of a tenant's screens that an event occurred."""
    tenant_id = tenant_id or get_current_tenant()
    if tenant_id is None:
        return

    layer = get_channel_layer()
    if layer is None:
        return

    final_payload: dict = {"event": event_type}
    if message is not None:
        final_payload["message"] = message
    if payload:
        final_payload.update(payload)

    try:
        async_to_sync(layer.group_send)(
            tenant_group_name(tenant_id),
            {"type": "tenant_event", "payload": final_payload},
        )
    except Exception:  # pragma: no cover
        logger.warning(f"Broadcast {event_type} failed", exc_info=True)


def broadcast_kds_update(
    *,
    tenant_id: uuid.UUID | None = None,
    message: str | None = None,
    kot_number: int | None = None,
    action: str | None = None,
) -> None:
    """Legacy helper for KDS specifically."""
    payload = {}
    if kot_number is not None:
        payload["kot_number"] = kot_number
    if action is not None:
        payload["action"] = action
    
    broadcast_tenant_event(
        "kds_changed",
        tenant_id=tenant_id,
        message=message,
        payload=payload,
    )
