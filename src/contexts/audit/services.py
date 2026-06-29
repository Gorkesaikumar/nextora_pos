"""Audit writer service.

Call from application services for security/financial events:

    record_audit("invoice.issued", entity_type="invoice", entity_id=inv.id,
                 changes={"number": inv.number})

Tenant, actor, and IP are pulled from request context automatically.
"""
import uuid
from typing import Any

from shared.infrastructure.logging.context import request_id_var
from shared.tenancy.context import get_current_tenant

from .context import get_actor_id, get_browser, get_correlation_id, get_device, get_ip_address
from .models import AuditLog


def record_audit(
    action: str,
    *,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    tenant_id = get_current_tenant()
    req_id = request_id_var.get(None)
    corr_id = correlation_id or get_correlation_id()
    new_val_final = new_value or changes or {}
    
    return AuditLog.objects.create(
        tenant_id=tenant_id,
        actor_id=get_actor_id(),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value or {},
        new_value=new_val_final,
        reason=reason,
        device=get_device(),
        browser=get_browser(),
        request_id=req_id,
        correlation_id=corr_id,
        ip_address=get_ip_address(),
    )
