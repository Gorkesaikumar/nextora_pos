"""Customer domain events (transactional outbox).

Events are written to the outbox inside the same transaction as the value-account
change, then delivered to handlers after commit. Importing this package (done in
``CustomersConfig.ready``) registers the handlers.
"""
from .domain_events import (
    CouponRedeemed,
    CreditCharged,
    CreditSettled,
    CustomerCreated,
    PointsEarned,
    PointsRedeemed,
    WalletSpent,
    WalletToppedUp,
)
from .publisher import (
    publish_coupon_redeemed,
    publish_credit_charged,
    publish_credit_settled,
    publish_customer_created,
    publish_points_earned,
    publish_points_redeemed,
    publish_wallet_spent,
    publish_wallet_topped_up,
)

# Importing handlers registers them with the shared event registry.
from . import handlers  # noqa: F401  (side-effect import)

__all__ = [
    "CouponRedeemed",
    "CreditCharged",
    "CreditSettled",
    "CustomerCreated",
    "PointsEarned",
    "PointsRedeemed",
    "WalletSpent",
    "WalletToppedUp",
    "publish_coupon_redeemed",
    "publish_credit_charged",
    "publish_credit_settled",
    "publish_customer_created",
    "publish_points_earned",
    "publish_points_redeemed",
    "publish_wallet_spent",
    "publish_wallet_topped_up",
]
