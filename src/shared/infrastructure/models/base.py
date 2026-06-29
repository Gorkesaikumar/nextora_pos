"""Reusable abstract base models — the persistence foundation for every
bounded context.

Composition over inheritance: each cross-cutting concern is a small abstract
mixin (ISP). Concrete models combine exactly the ones they need:

    class Order(TenantOwnedModel, BaseModel):
        ...

Mixins
------
* UUIDModel       — UUIDv4 primary key (non-enumerable, client-generatable).
* TimeStampedModel— created_at / updated_at (auto, indexed).
* AuditModel      — created_by / updated_by (actor UUIDs, no cross-app FK).
* SoftDeleteModel — is_deleted / deleted_at + soft-delete managers.
* BaseModel       — the common stack: UUID + timestamps + audit + soft delete.
"""
import uuid

from django.db import models
from django.utils import timezone

from .managers import AllObjectsManager, SoftDeleteManager, SoftDeleteQuerySet


class AuditModelTrackerMixin:
    """Automatically records Create, Update, and Delete actions to the audit log."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_state = self._get_current_state()

    def _get_current_state(self) -> dict:
        from datetime import date, datetime, time
        from decimal import Decimal
        from django.db.models.fields.files import FieldFile
        state = {}
        deferred_fields = self.get_deferred_fields()
        for field in self._meta.fields:
            if field.attname in deferred_fields:
                continue
            val = getattr(self, field.attname)
            if isinstance(val, uuid.UUID):
                val = str(val)
            elif isinstance(val, (datetime, date, time)):
                val = val.isoformat()
            elif isinstance(val, Decimal):
                val = str(val)
            elif isinstance(val, FieldFile):
                val = val.name if val else None
            elif val is not None and not isinstance(val, (str, int, float, bool, dict, list, tuple)):
                val = str(val)
            state[field.attname] = val
        return state



    def save(self, *args, **kwargs):
        is_creation = self._state.adding
        super().save(*args, **kwargs)
        
        new_state = self._get_current_state()
        old_val, new_val = {}, {}
        
        if is_creation:
            action = "database.create"
            new_val = new_state
        else:
            action = "database.update"
            for k, v in new_state.items():
                old_v = self._initial_state.get(k)
                if old_v != v:
                    old_val[k] = old_v
                    new_val[k] = v
                    
        # Exclude tracking updates to purely internal maintenance timestamps
        # unless something else changed
        if not is_creation and list(new_val.keys()) == ["updated_at"]:
            return

        if old_val or new_val:
            from contexts.audit.services import record_audit
            record_audit(
                action=action,
                entity_type=self._meta.db_table,
                entity_id=self.pk,
                old_value=old_val,
                new_value=new_val,
            )
        self._initial_state = new_state


class UUIDModel(models.Model):
    """Primary key is a random UUIDv4.

    Why UUID, not auto-increment:
      * Not enumerable — prevents resource-guessing across tenants.
      * Client-generatable — enables idempotent writes and future offline sync.
      * Globally unique — safe to merge across partitions / shards / replicas.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Self-maintaining created/updated timestamps (UTC)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(models.Model):
    """Who created / last changed the row.

    Actors are stored as UUIDs rather than FKs to ``identity.User`` so that:
      * tables in any context don't all hard-depend on the user table, and
      * audit rows survive even if a user record is later removed.
    The service layer is responsible for stamping these from request context.
    """

    created_by = models.UUIDField(null=True, blank=True, editable=False)
    updated_by = models.UUIDField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Reversible deletion.

    ``delete()`` flips the flag instead of issuing SQL DELETE. Use
    ``hard_delete()`` for the rare genuine purge (e.g. GDPR erasure that does
    not conflict with financial-record retention).
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    # Default manager hides deleted rows; all_objects sees everything.
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["is_deleted", "deleted_at"])
        
        from contexts.audit.services import record_audit
        record_audit(
            action="database.delete",
            entity_type=self._meta.db_table,
            entity_id=self.pk,
            old_value=self._get_current_state(),
            reason="Soft deleted",
        )

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseModel(AuditModelTrackerMixin, UUIDModel, TimeStampedModel, AuditModel, SoftDeleteModel):
    """The standard model stack for domain tables.

    UUID PK + timestamps + audit actors + soft delete. Most concrete models
    should extend this (and TenantOwnedModel once the tenancy context lands).
    """

    class Meta:
        abstract = True
        get_latest_by = "created_at"
        ordering = ["-created_at"]


__all__ = [
    "AllObjectsManager",
    "AuditModel",
    "BaseModel",
    "SoftDeleteManager",
    "SoftDeleteModel",
    "SoftDeleteQuerySet",
    "TimeStampedModel",
    "UUIDModel",
]
