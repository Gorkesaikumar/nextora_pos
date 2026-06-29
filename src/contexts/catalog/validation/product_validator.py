"""Validation rules for products, variants and combos."""
import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from contexts.catalog.domain.enums import ProductType
from contexts.catalog.exceptions import ValidationError
from contexts.catalog.repositories import ProductRepository

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")          # ISO-4217 alpha code
_HSN_RE = re.compile(r"^\d{4,8}$")                # 4–8 digit HSN/SAC


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _check_common(
    data: dict[str, Any], errors: dict[str, str], *, partial: bool
) -> None:
    """Field-level rules shared by create and update.

    ``partial`` skips presence checks for fields absent from an update payload.
    """
    if "name" in data or not partial:
        if not str(data.get("name") or "").strip():
            errors["name"] = "Name is required."

    if "base_price" in data or not partial:
        price = _as_decimal(data.get("base_price"))
        if price is None:
            errors["base_price"] = "Price must be a number."
        elif price < 0:
            errors["base_price"] = "Price cannot be negative."

    currency = data.get("currency")
    if currency is not None and not _CURRENCY_RE.match(str(currency)):
        errors["currency"] = "Currency must be a 3-letter ISO code (e.g. INR)."

    hsn = data.get("hsn_code")
    if hsn:  # optional, but if present must look like an HSN/SAC code
        if not _HSN_RE.match(str(hsn)):
            errors["hsn_code"] = "HSN/SAC code must be 4–8 digits."

    ptype = data.get("type")
    if ptype is not None and ptype not in ProductType.values:
        errors["type"] = f"Unknown product type '{ptype}'."


def validate_new_product(
    data: dict[str, Any], *, repo: ProductRepository | None = None
) -> None:
    """Validate a create payload. Raises ``ValidationError`` on any problem."""
    repo = repo or ProductRepository()
    errors: dict[str, str] = {}

    _check_common(data, errors, partial=False)

    sku = str(data.get("sku") or "").strip()
    if not sku:
        errors["sku"] = "SKU is required."
    elif repo.sku_exists(sku):
        errors["sku"] = f"SKU '{sku}' already exists."

    barcode = data.get("barcode")
    if barcode and repo.barcode_exists(str(barcode)):
        errors["barcode"] = f"Barcode '{barcode}' already exists."

    if not data.get("category"):
        errors["category"] = "Category is required."

    if errors:
        raise ValidationError(errors)


def validate_product_changes(
    product_id: uuid.UUID,
    changes: dict[str, Any],
    *,
    repo: ProductRepository | None = None,
) -> None:
    """Validate an update payload against the existing product."""
    repo = repo or ProductRepository()
    errors: dict[str, str] = {}

    _check_common(changes, errors, partial=True)

    if "sku" in changes:
        sku = str(changes.get("sku") or "").strip()
        if not sku:
            errors["sku"] = "SKU is required."
        elif repo.sku_exists(sku, exclude_id=product_id):
            errors["sku"] = f"SKU '{sku}' already exists."

    if changes.get("barcode") and repo.barcode_exists(
        str(changes["barcode"]), exclude_id=product_id
    ):
        errors["barcode"] = f"Barcode '{changes['barcode']}' already exists."

    if errors:
        raise ValidationError(errors)


def validate_combo_item(combo: Any, component: Any, quantity: Any) -> None:
    """A combo line must reference a combo parent and a distinct component."""
    errors: dict[str, str] = {}

    if getattr(combo, "type", None) != ProductType.COMBO:
        errors["combo"] = "Combo items can only be added to a COMBO product."
    if getattr(combo, "id", object()) == getattr(component, "id", None):
        errors["component"] = "A combo cannot contain itself."

    qty = _as_decimal(quantity)
    if qty is None or qty <= 0:
        errors["quantity"] = "Quantity must be greater than zero."

    if errors:
        raise ValidationError(errors)
