"""Gateway selection from settings (Twelve-Factor)."""
from functools import lru_cache

from django.conf import settings

from .base import PaymentGateway
from .fake import FakeGateway
from .razorpay import RazorpayGateway

_REGISTRY = {
    "fake": FakeGateway,
    "razorpay": RazorpayGateway,
}


@lru_cache(maxsize=1)
def get_gateway() -> PaymentGateway:
    name = getattr(settings, "BILLING_GATEWAY", "fake")
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown BILLING_GATEWAY: {name}") from exc


def reset_gateway_cache() -> None:
    """For tests that switch BILLING_GATEWAY at runtime."""
    get_gateway.cache_clear()
