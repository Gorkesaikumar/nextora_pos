"""Tests for the catalog validation layer."""
from decimal import Decimal

import pytest

from contexts.catalog.domain.enums import ProductType
from contexts.catalog.exceptions import CategoryCycle, ValidationError
from contexts.catalog.models import Category, Product
from contexts.catalog.validation import (
    validate_combo_item,
    validate_new_product,
    validate_product_changes,
    validate_reparent,
)

pytestmark = pytest.mark.django_db


def _category(name="Food", parent=None):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    return Category.objects.create(name=f"{name}-{suffix}", slug=f"{name.lower()}-{suffix}", parent=parent)


def _payload(**overrides):
    data = {
        "category": _category(),
        "name": "Burger",
        "sku": "BUR1",
        "base_price": Decimal("150.00"),
        "currency": "INR",
    }
    data.update(overrides)
    return data


# --- Product create rules --------------------------------------------------
def test_valid_payload_passes(active_tenant):
    validate_new_product(_payload())  # no raise


def test_missing_name_and_sku_collects_field_errors(active_tenant):
    with pytest.raises(ValidationError) as exc:
        validate_new_product(_payload(name="", sku=""))
    assert set(exc.value.errors) == {"name", "sku"}


def test_negative_price_rejected(active_tenant):
    with pytest.raises(ValidationError) as exc:
        validate_new_product(_payload(base_price=Decimal("-1")))
    assert "base_price" in exc.value.errors


def test_bad_currency_rejected(active_tenant):
    with pytest.raises(ValidationError) as exc:
        validate_new_product(_payload(currency="rupee"))
    assert "currency" in exc.value.errors


def test_bad_hsn_rejected(active_tenant):
    with pytest.raises(ValidationError) as exc:
        validate_new_product(_payload(hsn_code="ABC"))
    assert "hsn_code" in exc.value.errors


def test_duplicate_sku_rejected(active_tenant):
    Product.objects.create(
        category=_category(), name="X", sku="DUP", base_price=Decimal("1")
    )
    with pytest.raises(ValidationError) as exc:
        validate_new_product(_payload(sku="DUP"))
    assert "sku" in exc.value.errors


# --- Product update rules --------------------------------------------------
def test_update_allows_same_sku_on_self(active_tenant):
    product = Product.objects.create(
        category=_category(), name="X", sku="KEEP", base_price=Decimal("1")
    )
    # Re-submitting its own SKU must not be flagged as a duplicate.
    validate_product_changes(product.id, {"sku": "KEEP"})


# --- Combo rules -----------------------------------------------------------
def test_combo_must_be_combo_type(active_tenant):
    cat = _category()
    food = Product.objects.create(
        category=cat, name="Food", sku="F1", base_price=Decimal("1"),
        type=ProductType.FOOD,
    )
    component = Product.objects.create(
        category=cat, name="Comp", sku="C1", base_price=Decimal("1")
    )
    with pytest.raises(ValidationError) as exc:
        validate_combo_item(food, component, Decimal("1"))
    assert "combo" in exc.value.errors


def test_combo_cannot_contain_itself(active_tenant):
    cat = _category()
    combo = Product.objects.create(
        category=cat, name="Meal", sku="MEAL", base_price=Decimal("1"),
        type=ProductType.COMBO,
    )
    with pytest.raises(ValidationError) as exc:
        validate_combo_item(combo, combo, Decimal("1"))
    assert "component" in exc.value.errors


# --- Category reparent rules ----------------------------------------------
def test_reparent_cycle_rejected(active_tenant):
    parent = _category("A")
    child = _category("B", parent=parent)
    with pytest.raises(CategoryCycle):
        validate_reparent(parent, child)


def test_reparent_to_none_is_allowed(active_tenant):
    cat = _category("Standalone")
    validate_reparent(cat, None)  # no raise
