"""Payment gateway PORT — the interface billing services depend on.

No concrete provider details leak into the domain/services. Adapters (Razorpay,
Fake) implement this contract.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GatewayOrder:
    id: str
    amount_minor: int
    currency: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GatewayEvent:
    event_id: str
    event_type: str
    order_id: str | None
    payment_id: str | None
    status: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentGateway(ABC):
    name: str = "base"

    @abstractmethod
    def create_order(
        self, amount_minor: int, currency: str, receipt: str,
        notes: dict[str, str] | None = None,
    ) -> GatewayOrder:
        """Create a payment order/intent and return its id."""

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify the webhook HMAC signature."""

    @abstractmethod
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify the frontend checkout payment signature."""

    @abstractmethod
    def parse_webhook_event(self, body: bytes) -> GatewayEvent:
        """Normalise a raw webhook body into a GatewayEvent."""
