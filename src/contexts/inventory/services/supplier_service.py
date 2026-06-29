"""Supplier setup service."""
import uuid
from typing import Any

from django.db import transaction

from contexts.inventory.exceptions import DuplicateCode, SupplierNotFound
from contexts.inventory.models import Supplier
from contexts.inventory.repositories import SupplierRepository
from contexts.inventory.services.audit import audit_event

_suppliers = SupplierRepository()


@transaction.atomic
def create_supplier(*, name: str, code: str = "", **fields: Any) -> Supplier:
    if code and _suppliers.code_exists(code):
        raise DuplicateCode({"code": f"Supplier code '{code}' already exists."})
    supplier = _suppliers.add(Supplier(name=name, code=code, **fields))
    audit_event(
        "supplier.created",
        entity_type="supplier",
        entity_id=supplier.id,
        values={"name": name, "code": code},
    )
    return supplier


@transaction.atomic
def update_supplier(supplier_id: uuid.UUID, changes: dict[str, Any]) -> Supplier:
    supplier = _suppliers.lock(supplier_id)
    if supplier is None:
        raise SupplierNotFound(str(supplier_id))

    new_code = changes.get("code")
    if new_code and _suppliers.code_exists(new_code, exclude_id=supplier.id):
        raise DuplicateCode({"code": f"Supplier code '{new_code}' already exists."})

    for field, value in changes.items():
        setattr(supplier, field, value)
    return _suppliers.save(supplier)
