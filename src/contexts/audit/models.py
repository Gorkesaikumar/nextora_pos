"""Append-only, tenant-scoped audit log.

Tamper-evidence requires that rows are never updated or deleted. This model:
  * is tenant-scoped (RLS-protected like any other tenant table),
  * has no soft-delete / updated_at,
  * overrides delete() to raise.

High write volume + time-series access -> UUIDv7 PK and time partitioning are
applied in the migration (PARTITION BY RANGE (occurred_at)).
"""
import uuid

from django.db import models
from django.utils import timezone

from shared.tenancy.managers import TenantManager, TenantUnscopedManager


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.PROTECT, related_name="+"
    )

    actor_id = models.UUIDField(null=True, blank=True)  # null = system action
    action = models.CharField(max_length=100)           # e.g. "invoice.issued"
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    device = models.CharField(max_length=100, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = TenantManager()
    all_objects = TenantUnscopedManager()

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(
                fields=["tenant", "occurred_at"],
                name="ix_audit__tenant_time",
            ),
            models.Index(
                fields=["tenant", "entity_type", "entity_id", "occurred_at"],
                name="ix_audit__entity",
            ),
            models.Index(
                fields=["tenant", "actor_id", "occurred_at"],
                name="ix_audit__actor",
            ),
        ]

    def delete(self, *args, **kwargs):  # noqa: D401 — append-only
        raise NotImplementedError("Audit log is append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.action} @ {self.occurred_at:%Y-%m-%d %H:%M:%S}"
