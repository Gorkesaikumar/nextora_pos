import hashlib
from functools import wraps
from uuid import UUID

from .base import delete_cache, delete_pattern, get_cache, set_cache


def get_tenant_cache(tenant_id: UUID) -> dict | None:
    return get_cache(f"tenant:{tenant_id}")


def set_tenant_cache(tenant_id: UUID, data: dict, timeout: int = 3600) -> bool:
    return set_cache(f"tenant:{tenant_id}", data, timeout)


def invalidate_tenant_cache(tenant_id: UUID) -> bool:
    return delete_cache(f"tenant:{tenant_id}")


def get_product_cache(tenant_id: UUID, product_id: UUID) -> dict | None:
    return get_cache(f"tenant:{tenant_id}:product:{product_id}")


def set_product_cache(tenant_id: UUID, product_id: UUID, data: dict, timeout: int = 3600) -> bool:
    return set_cache(f"tenant:{tenant_id}:product:{product_id}", data, timeout)


def invalidate_product_cache(tenant_id: UUID, product_id: UUID) -> bool:
    return delete_cache(f"tenant:{tenant_id}:product:{product_id}")


def get_subscription_cache(tenant_id: UUID) -> dict | None:
    return get_cache(f"tenant:{tenant_id}:subscription")


def set_subscription_cache(tenant_id: UUID, data: dict, timeout: int = 3600) -> bool:
    return set_cache(f"tenant:{tenant_id}:subscription", data, timeout)


def invalidate_subscription_cache(tenant_id: UUID) -> bool:
    return delete_cache(f"tenant:{tenant_id}:subscription")


def get_permission_cache(tenant_id: UUID, user_id: UUID) -> list | None:
    return get_cache(f"tenant:{tenant_id}:perms:user:{user_id}")


def set_permission_cache(tenant_id: UUID, user_id: UUID, permissions: list, timeout: int = 3600) -> bool:
    return set_cache(f"tenant:{tenant_id}:perms:user:{user_id}", permissions, timeout)


def invalidate_permission_cache(tenant_id: UUID, user_id: UUID) -> bool:
    return delete_cache(f"tenant:{tenant_id}:perms:user:{user_id}")


def get_dashboard_cache(tenant_id: UUID, range_key: str) -> dict | None:
    return get_cache(f"tenant:{tenant_id}:dashboard:{range_key}")


def set_dashboard_cache(tenant_id: UUID, range_key: str, data: dict, timeout: int = 600) -> bool:
    return set_cache(f"tenant:{tenant_id}:dashboard:{range_key}", data, timeout)


def invalidate_dashboard_cache(tenant_id: UUID) -> bool:
    """Clear all cached dashboards for a specific tenant."""
    return delete_pattern(f"tenant:{tenant_id}:dashboard:*")


def cached_query(ttl: int = 600):
    """Decorator to cache function execution results using a tenant-scoped query key.

    The wrapped function must accept tenant_id as a parameter.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract tenant_id from kwargs or first positional argument
            tenant_id = kwargs.get("tenant_id")
            if not tenant_id and args:
                tenant_id = args[0]

            if not tenant_id:
                # If tenant context is missing, skip cache and execute query directly
                return func(*args, **kwargs)

            # Generate md5 hash of function inputs to build unique cache signature
            arg_str = f"{args}:{kwargs}"
            arg_hash = hashlib.md5(arg_str.encode("utf-8")).hexdigest()
            cache_key = f"query:{tenant_id}:{func.__name__}:{arg_hash}"

            cached = get_cache(cache_key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            set_cache(cache_key, result, timeout=ttl)
            return result

        return wrapper
    return decorator
