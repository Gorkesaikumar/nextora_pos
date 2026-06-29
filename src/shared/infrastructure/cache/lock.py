import logging
import time
import uuid
from contextlib import contextmanager
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Fallback local dictionary for lock stubbing in non-Redis/test environments
_LOCAL_LOCKS: dict[str, str] = {}


@contextmanager
def distributed_lock(
    lock_name: str,
    expire: int = 30,
    blocking: bool = True,
    timeout: int = 10,
):
    """Acquires a distributed lock using Redis, falling back to local memory stubs in tests.

    Crucially, it uses a Lua release script to ensure that workers only
    delete locks they currently own.
    """
    lock_key = f"lock:{lock_name}"
    token = str(uuid.uuid4())
    start_time = time.time()
    acquired = False

    # Get underlying Redis client if available
    client = None
    try:
        if hasattr(cache, "client") and hasattr(cache.client, "get_client"):
            # Using django-redis backend client
            client = cache.client.get_client()
    except Exception:
        pass

    while not acquired:
        if client is not None:
            try:
                # SET lock_key token NX PX (expire in milliseconds)
                acquired = client.set(lock_key, token, nx=True, px=expire * 1000)
            except Exception as e:
                logger.error(f"Redis distributed lock acquire error: {e}")
                # For safety, raise exception so we do not run critical blocks unlocked
                raise RuntimeError(f"Could not connect to distributed lock coordinator for: {lock_name}")
        else:
            # Fallback stub for unit tests / local development without Redis
            if lock_key not in _LOCAL_LOCKS:
                _LOCAL_LOCKS[lock_key] = token
                acquired = True
            elif not blocking:
                break

        if acquired:
            break
        if not blocking:
            break
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Could not acquire lock for {lock_name} within {timeout} seconds.")
        time.sleep(0.1)

    try:
        yield acquired
    finally:
        if acquired:
            if client is not None:
                try:
                    # Safe Lua script release
                    lua_release = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    client.eval(lua_release, 1, lock_key, token)
                except Exception as e:
                    logger.error(f"Failed to release distributed lock for {lock_name}: {e}")
            else:
                # Fallback release
                if _LOCAL_LOCKS.get(lock_key) == token:
                    _LOCAL_LOCKS.pop(lock_key, None)
