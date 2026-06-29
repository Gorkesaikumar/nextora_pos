"""Handlers for customer events.

Handlers run asynchronously (shared Celery dispatch) and receive the event
**payload dict** — they must be idempotent. Registered by importing this module
from ``CustomersConfig.ready``.

Privacy note: event payloads carry ids only (no PII), so handlers, the outbox
table and logs never persist personal data.
"""
import logging

from django.core.cache import cache

from shared.infrastructure.events.registry import register_handler

logger = logging.getLogger("nextora.customers.events")

_CUSTOMER_CACHE_KEY = "customer:summary:{customer_id}"


def invalidate_customer_cache(customer_id: str | None) -> None:
    if customer_id:
        cache.delete(_CUSTOMER_CACHE_KEY.format(customer_id=customer_id))


@register_handler("PointsEarned")
def on_points_earned(payload: dict) -> None:
    invalidate_customer_cache(payload.get("customer_id"))


@register_handler("PointsRedeemed")
def on_points_redeemed(payload: dict) -> None:
    invalidate_customer_cache(payload.get("customer_id"))


@register_handler("WalletToppedUp")
def on_wallet_topped_up(payload: dict) -> None:
    invalidate_customer_cache(payload.get("customer_id"))


@register_handler("WalletSpent")
def on_wallet_spent(payload: dict) -> None:
    invalidate_customer_cache(payload.get("customer_id"))


@register_handler("CreditCharged")
def on_credit_charged(payload: dict) -> None:
    invalidate_customer_cache(payload.get("customer_id"))


@register_handler("CouponRedeemed")
def on_coupon_redeemed(payload: dict) -> None:
    # Subscription point for offers/campaign analytics.
    logger.info("customers.coupon.redeemed", extra={"code": payload.get("code")})
