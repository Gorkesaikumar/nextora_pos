"""KDS WebSocket consumer.

One socket per kitchen screen. The consumer authenticates the session user,
resolves their tenant (mirroring the HTTP TenantResolutionMiddleware so a
tampered session can never join another tenant's group), and subscribes to the
tenant's KDS broadcast group. It is broadcast-only: clients never send data over
the socket — kitchen actions go through the permission-checked HTTP endpoints,
and the server fans a tiny "changed" signal back out to every screen.
"""
import logging
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger("nextora.kds")

_INACTIVE_STATUSES = {"suspended", "churned"}


def tenant_group_name(tenant_id: uuid.UUID) -> str:
    """Channel-layer group for a tenant's broadcast events (hex: no group-name chars)."""
    return f"tenant_{uuid.UUID(str(tenant_id)).hex}"


def resolve_ws_tenant(user, session) -> uuid.UUID | None:
    """Resolve which tenant a socket user may join (synchronous, DB-touching).

    Mirrors the HTTP TenantResolutionMiddleware's user/session fallback so a
    tampered session can never join a tenant the user does not belong to.
    """
    from contexts.identity.models import Membership
    from shared.tenancy.context import bypass_tenant

    # No tenant is bound on the socket scope, so bypass the fail-closed manager.
    with bypass_tenant():
        memberships = list(
            Membership.objects.filter(
                user=user, is_active=True, tenant__isnull=False
            ).select_related("tenant")
        )
    memberships = [
        m for m in memberships if m.tenant.status not in _INACTIVE_STATUSES
    ]
    if not memberships:
        return None

    # Honour the workspace picked in the session, but only if the user genuinely
    # belongs to it (same guard as the HTTP middleware).
    chosen = session.get("active_tenant_id") if session else None
    membership = None
    if chosen:
        membership = next(
            (m for m in memberships if str(m.tenant_id) == str(chosen)), None
        )
    if membership is None:
        membership = memberships[0]
    return membership.tenant_id


class TenantEventsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)  # unauthenticated
            return

        tenant_id = await self._resolve_tenant(user, self.scope.get("session"))
        if tenant_id is None:
            await self.close(code=4403)  # no tenant the user may access
            return

        self.tenant_id = tenant_id
        self.group_name = tenant_group_name(tenant_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        group = getattr(self, "group_name", None)
        if group is not None:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def tenant_event(self, event: dict) -> None:
        """Group fan-out handler — relay the broadcast payload to the browser."""
        await self.send_json(event["payload"])

    async def kds_event(self, event: dict) -> None:
        """Legacy handler for backward compatibility, routes to tenant_event."""
        await self.send_json(event["payload"])

    async def _resolve_tenant(self, user, session) -> uuid.UUID | None:
        return await database_sync_to_async(resolve_ws_tenant)(user, session)


# Backward compatibility aliases for KDS integration tests and legacy consumers
KDSConsumer = TenantEventsConsumer
kds_group_name = tenant_group_name
resolve_kds_tenant = resolve_ws_tenant

