import hashlib

from django.core.cache import cache

from contexts.features.models import FeatureFlag, RuleType


def _get_flag_cache_key(key: str) -> str:
    return f"feature_flag:{key}"


def _hash_bucket(hash_key: str, flag_key: str) -> int:
    """Returns a deterministic bucket from 1 to 100 based on the hash of the key."""
    hash_input = f"{flag_key}:{hash_key}".encode("utf-8")
    hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)
    return (hash_val % 100) + 1


def _load_flag_from_db(key: str) -> dict | None:
    try:
        flag = FeatureFlag.objects.get(key=key, is_deleted=False)
        rules = list(flag.rules.filter(is_deleted=False))
        return {
            "key": flag.key,
            "default_state": flag.default_state,
            "is_kill_switch": flag.is_kill_switch,
            "rules": [
                {
                    "rule_type": r.rule_type,
                    "target_value": r.target_value,
                    "is_enabled": r.is_enabled,
                }
                for r in rules
            ]
        }
    except FeatureFlag.DoesNotExist:
        return None


def evaluate_flag(key: str, context: dict) -> bool:
    """
    Evaluates a feature flag based on context.
    
    Context keys:
    - tenant_id (str)
    - subscription_tier (str)
    - country (str)
    - hash_key (str) - Defaults to tenant_id if not provided
    """
    cache_key = _get_flag_cache_key(key)
    flag_data = cache.get(cache_key)
    
    if flag_data is None:
        flag_data = _load_flag_from_db(key)
        if flag_data is None:
            return False
        cache.set(cache_key, flag_data, timeout=3600)

    if flag_data["is_kill_switch"]:
        return False

    for rule in flag_data["rules"]:
        rule_type = rule["rule_type"]
        target_value = rule["target_value"]
        is_enabled = rule["is_enabled"]

        if rule_type == RuleType.TENANT:
            if str(context.get("tenant_id")) in target_value:
                return is_enabled
                
        elif rule_type == RuleType.SUBSCRIPTION:
            if str(context.get("subscription_tier")) in target_value:
                return is_enabled
                
        elif rule_type == RuleType.COUNTRY:
            if str(context.get("country")) in target_value:
                return is_enabled
                
        elif rule_type in (RuleType.PERCENTAGE, RuleType.AB_TEST):
            hash_key = context.get("hash_key") or context.get("tenant_id")
            if not hash_key:
                continue
            bucket = _hash_bucket(str(hash_key), key)
            if bucket <= int(target_value):
                return is_enabled

    return flag_data["default_state"]


def bulk_evaluate(keys: list[str], context: dict) -> dict[str, bool]:
    """Evaluates multiple flags at once, useful for UI initialization."""
    return {key: evaluate_flag(key, context) for key in keys}
