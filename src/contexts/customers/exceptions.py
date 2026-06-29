"""Customer domain error hierarchy.

Services raise these typed exceptions; the API maps them to HTTP codes. The
value-account errors (wallet/points/credit) are financial — they must surface
clearly rather than silently clamping.
"""
from decimal import Decimal


class CustomerError(Exception):
    """Base for all customer-context errors."""


class CustomerNotFound(CustomerError):
    pass


class ValidationError(CustomerError):
    """Inputs failed validation. Carries a ``field -> message`` map."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


class InsufficientWalletBalance(CustomerError):
    def __init__(self, available: Decimal, requested: Decimal):
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient wallet balance. Available: {available}, Requested: {requested}"
        )


class InsufficientPoints(CustomerError):
    """Redeeming more points than the customer holds (never silently clamp)."""

    def __init__(self, available: int, requested: int):
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient loyalty points. Available: {available}, Requested: {requested}"
        )


class CreditLimitExceeded(CustomerError):
    def __init__(self, limit: Decimal, attempted_outstanding: Decimal):
        self.limit = limit
        self.attempted_outstanding = attempted_outstanding
        super().__init__(
            f"Store-credit limit {limit} exceeded (would reach {attempted_outstanding})."
        )


class CouponError(CustomerError):
    """Coupon invalid, expired, exhausted, or already used by this customer."""
