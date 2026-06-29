import logging

from django.http import HttpResponse
from prometheus_client import Gauge

from shared.api.health import _check_database, _check_redis

logger = logging.getLogger(__name__)

# Global Gauges for DB and Redis status
DATABASE_HEALTHY = Gauge("database_healthy", "Database health status (1 = healthy, 0 = degraded)")
REDIS_HEALTHY = Gauge("redis_healthy", "Redis cache/broker health status (1 = healthy, 0 = degraded)")


def metrics_view(request) -> HttpResponse:
    """Overridden metrics view.

    Dynamically queries database and Redis health on every Prometheus scrape,
    updating Gauges before exporting the metrics registry.
    """
    try:
        DATABASE_HEALTHY.set(1 if _check_database() else 0)
    except Exception as e:
        logger.error(f"Metrics db health check failed: {e}")
        DATABASE_HEALTHY.set(0)

    try:
        REDIS_HEALTHY.set(1 if _check_redis() else 0)
    except Exception as e:
        logger.error(f"Metrics redis health check failed: {e}")
        REDIS_HEALTHY.set(0)

    # Lazy import to avoid loading issues when django_prometheus is not enabled
    from django_prometheus.exports import ExportToDjangoView
    return ExportToDjangoView(request)
