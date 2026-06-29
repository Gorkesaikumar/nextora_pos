import hashlib
import logging
from uuid import UUID

from django.core.cache import cache

from .providers import SearchRegistry

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "search:"
CACHE_TIMEOUT = 300  # 5 minutes


def _get_cache_key(tenant_id: UUID, entity_type: str, query: str, limit: int, offset: int) -> str:
    cleaned_query = query.strip().lower()
    query_hash = hashlib.md5(cleaned_query.encode("utf-8")).hexdigest()
    return f"{CACHE_KEY_PREFIX}{tenant_id}:{entity_type}:{query_hash}:{limit}:{offset}"


def universal_search(
    query: str,
    tenant_id: UUID,
    entity_type: str = "all",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Performs a multi-entity or single-entity search, sorted by ranking, with caching."""
    if not query or len(query.strip()) < 2:
        return {"count": 0, "results": []}

    cache_key = _get_cache_key(tenant_id, entity_type, query, limit, offset)
    cached_results = cache.get(cache_key)
    if cached_results is not None:
        return cached_results

    results = []

    if entity_type == "all":
        # Search all providers, merge results, and rank
        providers = SearchRegistry.list_providers()
        for name, provider in providers.items():
            try:
                # Get more than the limit from each provider to allow global ranking
                provider_results = provider.search(query, tenant_id, limit=limit + offset, offset=0)
                results.extend(provider_results)
            except Exception as e:
                logger.error(f"Search provider '{name}' failed: {e}")

        # Rank merged results globally
        results.sort(key=lambda x: x["rank"], reverse=True)
        total_count = len(results)
        paginated_results = results[offset : offset + limit]
    else:
        # Search specific provider
        provider = SearchRegistry.get(entity_type)
        if not provider:
            raise ValueError(f"Unknown search entity type: {entity_type}")
            
        paginated_results = provider.search(query, tenant_id, limit=limit, offset=offset)
        # For single provider, the count is simply estimated/returned
        total_count = len(paginated_results)  # Simplified count for stubs

    response_payload = {"count": total_count, "results": paginated_results}
    cache.set(cache_key, response_payload, timeout=CACHE_TIMEOUT)
    return response_payload


def invalidate_search_cache(tenant_id: UUID) -> None:
    """Clears search caches for a tenant (called on model save/delete)."""
    # In Redis, we can delete keys matching prefix using scan / clear.
    # Since standard django cache.delete_many doesn't support wildcard,
    # we use cache.delete_pattern if using django-redis.
    try:
        cache.delete_pattern(f"{CACHE_KEY_PREFIX}{tenant_id}:*")
    except AttributeError:
        # Fallback for LocMemCache / non-redis backends to scan keys (useful in tests/dev)
        if hasattr(cache, "_cache"):
            prefix = f"{CACHE_KEY_PREFIX}{tenant_id}:"
            to_delete = []
            for k in list(cache._cache.keys()):
                parts = k.split(":", 2)
                raw_key = parts[-1] if len(parts) >= 3 else k
                if raw_key.startswith(prefix) or prefix in k:
                    to_delete.append(raw_key)
            for rk in to_delete:
                cache.delete(rk)
