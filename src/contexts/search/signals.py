from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from contexts.catalog.models import Category, Product
from contexts.identity.models import Membership
from contexts.ordering.models import Invoice
from contexts.customers.models import Customer
from contexts.inventory.models.supplier import Supplier
from .services import invalidate_search_cache


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Invoice)
@receiver([post_save, post_delete], sender=Customer)
@receiver([post_save, post_delete], sender=Supplier)
def clear_search_cache_on_change(sender, instance, **kwargs):
    tenant_id = getattr(instance, "tenant_id", None)
    if tenant_id:
        invalidate_search_cache(tenant_id)


@receiver([post_save, post_delete], sender=Membership)
def clear_search_cache_on_member_change(sender, instance, **kwargs):
    tenant_id = getattr(instance, "tenant_id", None)
    if tenant_id:
        invalidate_search_cache(tenant_id)
