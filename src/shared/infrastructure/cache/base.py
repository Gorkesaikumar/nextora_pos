import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_cache(key: str, default=None):
    """Retrieve value from cache. Fails open on connection issues."""
    try:
        return cache.get(key, default)
    except Exception as e:
        logger.error(f"Redis get failed for key {key}: {e}", exc_info=True)
        return default


def set_cache(key: str, value, timeout: int = 3600) -> bool:
    """Save value to cache. Fails open on connection issues."""
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception as e:
        logger.error(f"Redis set failed for key {key}: {e}", exc_info=True)
        return False


def delete_cache(key: str) -> bool:
    """Delete key from cache. Fails open on connection issues."""
    try:
        cache.delete(key)
        return True
    except Exception as e:
        logger.error(f"Redis delete failed for key {key}: {e}", exc_info=True)
        return False


def delete_pattern(pattern: str) -> bool:
    """Delete keys matching pattern. Fails open on connection issues."""
    try:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
        else:
            # Fallback if cache backend doesn't support delete_pattern
            pass
        return True
    except Exception as e:
        logger.error(f"Redis delete_pattern failed for pattern {pattern}: {e}", exc_info=True)
        return False
