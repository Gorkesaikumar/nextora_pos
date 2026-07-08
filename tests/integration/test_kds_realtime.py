"""KDS real-time (Channels/WebSocket) coverage.

Split so none of it depends on cross-thread DB visibility (which sqlite's
in-memory test DB does not provide):

* Tenant resolution is exercised synchronously with the normal ``db`` fixture.
* The socket lifecycle / broadcast fan-out is exercised over an in-memory
  channel layer with the DB-touching resolver patched out.
"""
import asyncio
import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.layers import channel_layers, get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from contexts.ordering.consumers import (
    KDSConsumer,
    kds_group_name,
    resolve_kds_tenant,
)
from contexts.ordering.realtime import broadcast_kds_update


@pytest.fixture
def in_memory_channel_layer(settings):
    """Force the in-process channel layer and reset the cached registry."""
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    channel_layers.backends = {}
    yield
    channel_layers.backends = {}


def _membership(tenant, user, role, **kwargs):
    from contexts.identity.models import Membership

    return Membership.objects.create(
        user=user, tenant=tenant, role=role, is_active=True, **kwargs
    )


# --- Tenant resolution (synchronous, real DB) -----------------------------

def test_resolve_returns_tenant_for_active_membership(tenant, make_user, system_role):
    user = make_user()
    _membership(tenant, user, system_role("company_owner"))

    assert resolve_kds_tenant(user, session={}) == tenant.id


def test_resolve_none_without_membership(make_user, db):
    user = make_user()
    assert resolve_kds_tenant(user, session={}) is None


def test_resolve_honours_session_choice_only_if_member(
    tenant, other_tenant, make_user, system_role
):
    user = make_user()
    _membership(tenant, user, system_role("company_owner"))

    # User does NOT belong to other_tenant — a tampered session must not win.
    chosen = resolve_kds_tenant(user, session={"active_tenant_id": str(other_tenant.id)})
    assert chosen == tenant.id


def test_resolve_skips_inactive_tenant(tenant, make_user, system_role):
    user = make_user()
    _membership(tenant, user, system_role("company_owner"))
    tenant.status = "suspended"
    tenant.save(update_fields=["status"])

    assert resolve_kds_tenant(user, session={}) is None


# --- Broadcast fan-out (in-memory layer, no DB) ---------------------------

def test_broadcast_reaches_subscribed_channel(in_memory_channel_layer):
    tenant_id = uuid.uuid4()

    # Drive the async fan-out from sync code.
    async def run():
        layer = get_channel_layer()
        chan = await layer.new_channel()
        await layer.group_add(kds_group_name(tenant_id), chan)
        # broadcast_kds_update is sync (uses async_to_sync internally), exactly as
        # the Django view calls it — run it off-loop in a worker thread.
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: broadcast_kds_update(
                tenant_id=tenant_id, message="hi", kot_number=3, action="READY"
            ),
        )
        msg = await layer.receive(chan)
        return msg

    msg = async_to_sync(run)()
    assert msg["type"] == "tenant_event"
    assert msg["payload"] == {
        "event": "kds_changed", "message": "hi", "kot_number": 3, "action": "READY",
    }


def test_broadcast_noop_without_tenant(in_memory_channel_layer):
    # No tenant in context and none passed -> silently does nothing (no raise).
    broadcast_kds_update(message="ignored")


# --- Consumer socket lifecycle (resolver patched) -------------------------

def test_consumer_accepts_authenticated_and_relays(in_memory_channel_layer, monkeypatch):
    tenant_id = uuid.uuid4()

    # Patch the resolver method to skip the DB/thread hop — tenant resolution is
    # covered by the synchronous tests above; here we test the socket lifecycle.
    async def _fake_resolve(self, user, session):
        return tenant_id

    monkeypatch.setattr(KDSConsumer, "_resolve_tenant", _fake_resolve)

    class _AuthedUser:
        is_authenticated = True

    async def run():
        comm = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
        comm.scope["user"] = _AuthedUser()
        comm.scope["session"] = {}
        connected, _ = await comm.connect()
        assert connected

        # Fan out on the consumer's loop (the broadcast *helper* is covered
        # separately; here we assert the consumer subscribed and relays).
        layer = get_channel_layer()
        await layer.group_send(
            kds_group_name(tenant_id),
            {"type": "kds_event", "payload": {"event": "changed", "message": "New order received."}},
        )
        payload = await comm.receive_json_from(timeout=2)
        await comm.disconnect()
        return payload

    payload = async_to_sync(run)()
    assert payload["event"] == "changed"
    assert payload["message"] == "New order received."


def test_consumer_rejects_anonymous(in_memory_channel_layer):
    async def run():
        comm = WebsocketCommunicator(KDSConsumer.as_asgi(), "/ws/kds/")
        comm.scope["user"] = AnonymousUser()
        comm.scope["session"] = {}
        connected, code = await comm.connect()
        return connected, code

    connected, code = async_to_sync(run)()
    assert connected is False
    assert code == 4401
