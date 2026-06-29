"""Razorpay adapter — integration-ready.

The razorpay SDK import is guarded so the package is optional until billing goes
live with real keys. Keys come from settings (Twelve-Factor: config). Webhook
signature verification follows Razorpay's HMAC-SHA256 scheme.
"""
import hashlib
import hmac
import json
from typing import Any

from django.conf import settings

from contexts.billing.exceptions import GatewayError

from .base import GatewayEvent, GatewayOrder, PaymentGateway


class RazorpayGateway(PaymentGateway):
    name = "razorpay"

    def __init__(self) -> None:
        self._key_id = settings.RAZORPAY_KEY_ID
        self._key_secret = settings.RAZORPAY_KEY_SECRET
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self._client = self._build_client()

    def _build_client(self):
        try:
            import razorpay  # noqa: PLC0415 — optional dependency
        except ImportError as exc:  # pragma: no cover
            raise GatewayError(
                "razorpay SDK not installed. `pip install razorpay` to enable."
            ) from exc
        return razorpay.Client(auth=(self._key_id, self._key_secret))

    def create_order(
        self, amount_minor: int, currency: str, receipt: str,
        notes: dict[str, str] | None = None,
    ) -> GatewayOrder:
        order = self._client.order.create(
            {
                "amount": amount_minor,         # Razorpay expects minor units
                "currency": currency,
                "receipt": receipt,
                "notes": notes or {},
            }
        )
        return GatewayOrder(
            id=order["id"],
            amount_minor=order["amount"],
            currency=order["currency"],
            raw=order,
        )

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        expected = hmac.new(
            self._webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    def parse_webhook_event(self, body: bytes) -> GatewayEvent:
        data: dict[str, Any] = json.loads(body.decode() or "{}")
        entity = (
            data.get("payload", {}).get("payment", {}).get("entity", {})
        )
        return GatewayEvent(
            event_id=data.get("id", ""),
            event_type=data.get("event", ""),
            order_id=entity.get("order_id"),
            payment_id=entity.get("id"),
            status=entity.get("status"),
            raw=data,
        )
