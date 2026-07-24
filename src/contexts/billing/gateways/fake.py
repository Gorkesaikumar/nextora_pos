"""Deterministic in-memory gateway for tests and local dev.

No network. Signature is an HMAC-SHA256 over the body using a known test secret,
so webhook verification can be exercised end-to-end without Razorpay.
"""
import hashlib
import hmac
import json
from typing import Any

from .base import GatewayEvent, GatewayOrder, PaymentGateway

FAKE_SECRET = "fake-webhook-secret"


class FakeGateway(PaymentGateway):
    name = "fake"

    def __init__(self, secret: str = FAKE_SECRET) -> None:
        self._secret = secret
        self._counter = 0

    def create_order(
        self, amount_minor: int, currency: str, receipt: str,
        notes: dict[str, str] | None = None,
    ) -> GatewayOrder:
        self._counter += 1
        return GatewayOrder(
            id=f"order_fake_{self._counter}",
            amount_minor=amount_minor,
            currency=currency,
            raw={"receipt": receipt, "notes": notes or {}},
        )

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret.encode(), body, hashlib.sha256).hexdigest()

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(body), signature or "")

    def parse_webhook_event(self, body: bytes) -> GatewayEvent:
        data: dict[str, Any] = json.loads(body.decode() or "{}")
        return GatewayEvent(
            event_id=data.get("id", ""),
            event_type=data.get("event", ""),
            order_id=data.get("order_id"),
            payment_id=data.get("payment_id"),
            status=data.get("status"),
            raw=data,
        )

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        # In the fake gateway, just accept anything or simulate a valid signature for tests
        return True
