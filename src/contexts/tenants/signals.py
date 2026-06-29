from django.db.models.signals import post_save
from django.dispatch import receiver

from shared.tenancy.scope import tenant_scope
from .models import Tenant, TenantConfiguration


@receiver(post_save, sender=Tenant)
def create_tenant_configuration(sender, instance, created, **kwargs):
    if created:
        with tenant_scope(instance.id):
            TenantConfiguration.objects.get_or_create(tenant=instance)
