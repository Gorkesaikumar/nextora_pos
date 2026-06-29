"""Inbound gateway webhook processing — verify, store idempotently, dispatch."""
from django.utils import timezone

from contexts.billing.exceptions import GatewayError
from contexts.billing.gateways import get_gateway
from contexts.billing.gateways.base import GatewayEvent
from contexts.billing.models import SubscriptionInvoice, WebhookEvent
from contexts.billing.services import invoice_service
from shared.tenancy import bypass_tenant

# Gateway event types that indicate a successful capture.
_PAID_EVENTS = {"payment.captured", "order.paid", "invoice.paid"}


def handle_webhook(body: bytes, signature: str) -> str:
    """Process a raw webhook. Returns 'processed' | 'duplicate' | 'ignored'."""
    gateway = get_gateway()
    if not gateway.verify_webhook_signature(body, signature):
        raise GatewayError("Invalid webhook signature.")

    event = gateway.parse_webhook_event(body)

    obj, created = WebhookEvent.objects.get_or_create(
        provider=gateway.name,
        event_id=event.event_id,
        defaults={"event_type": event.event_type, "payload": event.raw},
    )
    if not created and obj.status == WebhookEvent.Status.PROCESSED:
        return "duplicate"

    try:
        result = _dispatch(gateway.name, event)
        obj.status = (
            WebhookEvent.Status.PROCESSED
            if result == "processed"
            else WebhookEvent.Status.IGNORED
        )
        obj.processed_at = timezone.now()
        obj.save(update_fields=["status", "processed_at", "updated_at"])
        return result
    except Exception as exc:  # noqa: BLE001 — record then re-raise
        obj.status = WebhookEvent.Status.FAILED
        obj.error = str(exc)
        obj.save(update_fields=["status", "error", "updated_at"])
        raise


def _dispatch(provider: str, event: GatewayEvent) -> str:
    if event.event_type not in _PAID_EVENTS or not event.order_id:
        return "ignored"

    with bypass_tenant():
        invoice = (
            SubscriptionInvoice.all_objects
            .filter(provider_order_id=event.order_id)
            .first()
        )
    if invoice is None:
        return "ignored"

    invoice_service.mark_paid(
        invoice.tenant_id,
        invoice,
        provider=provider,
        provider_payment_id=event.payment_id or "",
    )
    return "processed"
