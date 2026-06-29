"""Invalidate cached authorization decisions on any RBAC change.

We bump a single global version counter rather than enumerating affected cache
keys. A role/permission change is rare relative to permission checks, so a full
invalidation is cheap and guarantees correctness (no stale grants).
"""
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from contexts.identity.models import Membership, Role, RolePermission
from contexts.identity.services.authorization import bump_version


@receiver([post_save, post_delete], sender=Membership)
@receiver([post_save, post_delete], sender=RolePermission)
@receiver([post_save, post_delete], sender=Role)
def _invalidate_on_change(sender, **kwargs) -> None:
    bump_version()


@receiver(m2m_changed, sender=Role.permissions.through)
def _invalidate_on_m2m(sender, **kwargs) -> None:
    if kwargs.get("action") in {"post_add", "post_remove", "post_clear"}:
        bump_version()
