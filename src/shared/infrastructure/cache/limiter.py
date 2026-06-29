import logging
import time
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Fallback local dictionary for rate limiting in test environments
_LOCAL_LIMITS: dict[str, list[float]] = {}


def is_rate_limited(key: str, limit: int, period: int) -> bool:
    """Sliding window rate limiter using Redis sorted sets.

    Falls back to a local memory sliding window in test/local environments.
    """
    now = time.time()
    clear_before = now - period

    client = None
    try:
        if hasattr(cache, "client") and hasattr(cache.client, "get_client"):
            client = cache.client.get_client()
    except Exception:
        pass

    if client is not None:
        try:
            redis_key = f"rate_limit:{key}"
            pipeline = client.pipeline()
            
            # 1. Clean up older scores
            pipeline.zremrangebyscore(redis_key, 0, clear_before)
            # 2. Add current timestamp
            pipeline.zadd(redis_key, {str(now): now})
            # 3. Read size of window
            pipeline.zcard(redis_key)
            # 4. Set expiry to cleanup idle limits
            pipeline.expire(redis_key, period)
            
            # Execute pipeline
            results = pipeline.execute()
            current_count = results[2]  # Output of zcard
            
            return current_count > limit
        except Exception as e:
            logger.error(f"Redis rate limiting error for key {key}: {e}")
            # Fail-open: do not block users if rate limiting engine has a glitch
            return False
    else:
        # Fallback local memory sliding window rate limiter
        history = [t for t in _LOCAL_LIMITS.get(key, []) if t > clear_before]
        if len(history) >= limit:
            return True
            
        history.append(now)
        _LOCAL_LIMITS[key] = history
        return False
