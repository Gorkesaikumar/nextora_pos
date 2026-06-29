"""Inventory error hierarchy.

Services raise these typed exceptions; the API layer maps them to HTTP codes.
Repositories return ``None`` — turning that into a typed not-found is the
service's job, so the "missing entity" decision lives in one place.
"""
from decimal import Decimal


class InventoryError(Exception):
    """Base for all inventory-context errors."""


# --- Not found -------------------------------------------------------------
class InventoryItemNotFound(InventoryError):
    pass


class WarehouseNotFound(InventoryError):
    pass


class SupplierNotFound(InventoryError):
    pass


class PurchaseOrderNotFound(InventoryError):
    pass


class PurchaseOrderLineNotFound(InventoryError):
    pass


class TransferNotFound(InventoryError):
    pass


class AdjustmentNotFound(InventoryError):
    pass


class AlertNotFound(InventoryError):
    pass


# --- Validation / business rules ------------------------------------------
class ValidationError(InventoryError):
    """One or more inputs failed validation. Carries a ``field -> message`` map."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


class DuplicateCode(ValidationError):
    """A unique code (warehouse/supplier) is already taken for this tenant."""


class InsufficientStock(InventoryError):
    """A stock-out would drive an item or batch below zero (BLOCK policy)."""

    def __init__(self, sku: str, available: Decimal, requested: Decimal):
        self.sku = sku
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for {sku}. Available: {available}, "
            f"Requested: {requested}"
        )


class InvalidStateTransition(InventoryError):
    """An operation is not allowed from the entity's current status."""

    def __init__(self, entity: str, current: str, action: str):
        self.entity = entity
        self.current = current
        self.action = action
        super().__init__(
            f"Cannot {action} a {entity} in status '{current}'."
        )
