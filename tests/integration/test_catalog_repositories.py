"""Tests for the catalog repository layer."""
from decimal import Decimal

import pytest

from contexts.catalog.models import Category, Product
from contexts.catalog.repositories import (
    CategoryRepository,
    ProductRepository,
)
from shared.tenancy import tenant_context

pytestmark = pytest.mark.django_db


def _category(name="Food", parent=None):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    return Category.objects.create(name=f"{name}-{suffix}", slug=f"{name.lower()}-{suffix}", parent=parent)


def _product(sku="SKU1", barcode=None, category=None, price="100.00"):
    return Product.objects.create(
        category=category or _category(),
        name="Item", sku=sku, barcode=barcode, base_price=Decimal(price),
    )


# --- ProductRepository -----------------------------------------------------
def test_get_returns_none_for_missing(active_tenant):
    import uuid

    assert ProductRepository().get(uuid.uuid4()) is None


def test_sku_exists_detects_live_product(active_tenant):
    repo = ProductRepository()
    product = _product(sku="LIVE")
    assert repo.sku_exists("LIVE") is True
    assert repo.sku_exists("LIVE", exclude_id=product.id) is False
    assert repo.sku_exists("NOPE") is False


def test_sku_exists_ignores_soft_deleted(active_tenant):
    repo = ProductRepository()
    product = _product(sku="GONE")
    product.delete()  # soft delete
    # Reusable after delete: the partial unique excludes deleted rows.
    assert repo.sku_exists("GONE") is False


def test_barcode_exists(active_tenant):
    repo = ProductRepository()
    _product(sku="B1", barcode="999")
    assert repo.barcode_exists("999") is True
    assert repo.barcode_exists("") is False
    assert repo.barcode_exists(None) is False


def test_repository_is_tenant_scoped(active_tenant, other_tenant):
    product = _product(sku="SCOPED")
    repo = ProductRepository()
    assert repo.get(product.id) is not None
    # The same repository, under another tenant's context, sees nothing.
    with tenant_context(other_tenant.id):
        assert repo.get(product.id) is None
        assert repo.sku_exists("SCOPED") is False


def test_list_for_category_eager_loads(active_tenant):
    cat = _category("Mains")
    _product(sku="M1", category=cat)
    qs = ProductRepository().list_for_category(cat.id)
    assert qs.count() == 1


# --- CategoryRepository ----------------------------------------------------
def test_ancestors_walks_to_root(active_tenant):
    root = _category("Beverages")
    mid = _category("Cold", parent=root)
    leaf = _category("Soda", parent=mid)

    ancestors = list(CategoryRepository().ancestors(leaf))
    assert [c.id for c in ancestors] == [mid.id, root.id]


def test_roots_and_children(active_tenant):
    repo = CategoryRepository()
    root = _category("Root")
    child = _category("Child", parent=root)

    assert root.id in {c.id for c in repo.roots()}
    assert child.id not in {c.id for c in repo.roots()}
    assert {c.id for c in repo.children_of(root.id)} == {child.id}
