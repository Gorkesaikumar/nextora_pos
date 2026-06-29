"""Warehouse setup service."""
import uuid
from typing import Any

from django.db import transaction

from contexts.inventory.exceptions import DuplicateCode, WarehouseNotFound
from contexts.inventory.models import Warehouse
from contexts.inventory.repositories import WarehouseRepository
from contexts.inventory.services.audit import audit_event

_warehouses = WarehouseRepository()


@transaction.atomic
def create_warehouse(
    *,
    name: str,
    code: str,
    branch_id: uuid.UUID | None = None,
    address: str = "",
    is_default: bool = False,
) -> Warehouse:
    if _warehouses.code_exists(code):
        raise DuplicateCode({"code": f"Warehouse code '{code}' already exists."})

    warehouse = Warehouse(
        name=name, code=code, branch_id=branch_id,
        address=address, is_default=is_default,
    )
    if is_default:
        _clear_existing_default(branch_id)
    warehouse = _warehouses.add(warehouse)

    audit_event(
        "warehouse.created",
        entity_type="warehouse",
        entity_id=warehouse.id,
        values={"code": code, "name": name, "branch_id": branch_id, "is_default": is_default},
    )
    return warehouse


@transaction.atomic
def set_default_warehouse(warehouse_id: uuid.UUID) -> Warehouse:
    warehouse = _warehouses.lock(warehouse_id)
    if warehouse is None:
        raise WarehouseNotFound(str(warehouse_id))

    _clear_existing_default(warehouse.branch_id, exclude_id=warehouse.id)
    warehouse.is_default = True
    return _warehouses.save(warehouse, update_fields=["is_default", "updated_at"])


@transaction.atomic
def update_warehouse(warehouse_id: uuid.UUID, changes: dict[str, Any]) -> Warehouse:
    warehouse = _warehouses.lock(warehouse_id)
    if warehouse is None:
        raise WarehouseNotFound(str(warehouse_id))

    new_code = changes.get("code")
    if new_code and _warehouses.code_exists(new_code, exclude_id=warehouse.id):
        raise DuplicateCode({"code": f"Warehouse code '{new_code}' already exists."})

    for field, value in changes.items():
        setattr(warehouse, field, value)
    return _warehouses.save(warehouse)


def _clear_existing_default(
    branch_id: uuid.UUID | None, *, exclude_id: uuid.UUID | None = None
) -> None:
    """Demote the current default so only one stays default.

    Scoped per branch where a branch is set (see ADR-0001 review W3: the DB
    constraint is still per-tenant and should be widened to (tenant, branch_id)).
    """
    qs = _warehouses.get_queryset().filter(is_default=True)
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    qs.update(is_default=False)
