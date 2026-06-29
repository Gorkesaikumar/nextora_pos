"""Operational health probes.

* /healthz/live/  — liveness:  is the process alive? Cheap, no deps. A failing
                    liveness probe means "restart me".
* /healthz/ready/ — readiness: are my dependencies (DB, Redis, cache) usable?
                    A failing readiness probe means "stop sending me traffic"
                    but does NOT trigger a restart.

Both are unauthenticated and tenant-agnostic — they are infrastructure probes.
"""
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpRequest, JsonResponse
from redis import Redis
from redis.exceptions import RedisError

from django.conf import settings


def liveness(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "alive"})


def _check_database() -> bool:
    try:
        connections["default"].cursor().execute("SELECT 1")
        return True
    except OperationalError:
        return False


def _check_cache() -> bool:
    try:
        cache.set("__healthcheck__", "1", timeout=5)
        return cache.get("__healthcheck__") == "1"
    except Exception:  # noqa: BLE001 — any cache failure means not-ready
        return False


def _check_redis() -> bool:
    try:
        client = Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        return bool(client.ping())
    except RedisError:
        return False


def readiness(request: HttpRequest) -> JsonResponse:
    checks = {
        "database": _check_database(),
        "cache": _check_cache(),
        "broker": _check_redis(),
    }
    healthy = all(checks.values())
    return JsonResponse(
        {"status": "ready" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )
