"""Thin audit helper for the inventory context.

Wraps the shared ``record_audit`` (which reads tenant/actor/ip from context),
JSON-serialising Decimal/UUID values for the audit log's JSON fields.

Scope note: the immutable StockMovement ledger is already the per-change record,
so we do **not** audit individual movements. These entries capture the
operationally/financially significant *document* events — receipts, approvals,
write-offs and configuration changes.
"""
import uuid
from decimal import Decimal
from typing import Any

from contexts.audit.services import record_audit


def _safe(value: Any) -> Any:
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    return value


def _safe_dict(values: dict[str, Any] | None) -> dict[str, Any] | None:
    if not values:
        return None
    return {k: _safe(v) for k, v in values.items()}


def audit_event(
    action: str,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    values: dict[str, Any] | None = None,
    old_values: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    record_audit(
        action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_safe_dict(old_values),
        new_value=_safe_dict(values),
        reason=reason,
    )
