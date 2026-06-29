"""Billing error hierarchy."""


class BillingError(Exception):
    """Base for all billing errors."""


class PlanNotFound(BillingError):
    pass


class PriceNotFound(BillingError):
    pass


class ActiveSubscriptionExists(BillingError):
    pass


class NoActiveSubscription(BillingError):
    pass


class LimitExceeded(BillingError):
    """A plan limit would be breached by the attempted action."""

    def __init__(self, metric: str, limit: int, current: int, requested: int):
        self.metric = metric
        self.limit = limit
        self.current = current
        self.requested = requested
        super().__init__(
            f"Limit '{metric}' exceeded: {current}+{requested} > {limit}."
        )


class GatewayError(BillingError):
    pass
