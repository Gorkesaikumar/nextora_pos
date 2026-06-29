from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from contexts.features.models import FeatureFlag, FeatureRule
from contexts.features.services import _get_flag_cache_key


@receiver([post_save, post_delete], sender=FeatureFlag)
def invalidate_flag_cache(sender, instance, **kwargs):
    cache.delete(_get_flag_cache_key(instance.key))


@receiver([post_save, post_delete], sender=FeatureRule)
def invalidate_rule_cache(sender, instance, **kwargs):
    # Rule changes should invalidate the parent flag's cache
    if hasattr(instance, "flag") and instance.flag:
        cache.delete(_get_flag_cache_key(instance.flag.key))
