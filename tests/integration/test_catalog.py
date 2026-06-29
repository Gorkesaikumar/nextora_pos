"""Catalog model + service tests."""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from contexts.audit.models import AuditLog
from contexts.catalog.exceptions import CategoryCycle
from contexts.catalog.models import (
    Category,
    KitchenStation,
    ModifierGroup,
    Product,
    ProductVariant,
    TaxClass,
)
from contexts.catalog.services import import_export, product_service

pytestmark = pytest.mark.django_db


def _category(name="Food", parent=None):
    import django.utils.text
    import uuid
    suffix = uuid.uuid4().hex[:6]
    slug = django.utils.text.slugify(name) or "cat"
    return Category.objects.create(name=name, slug=f"{slug}-{suffix}", parent=parent)


def _product(sku="SKU1", name="Item", barcode=None, category=None, price="100.00"):
    return Product.objects.create(
        category=category or _category(),
        name=name, sku=sku, barcode=barcode, base_price=Decimal(price),
    )


# --- Creation + audit ------------------------------------------------------
def test_create_product_via_service_records_audit(active_tenant):
    category = _category()
    product = product_service.create_product(
        {"category": category, "name": "Burger", "sku": "BUR1",
         "base_price": Decimal("150.00")}
    )
    assert product.tenant_id == active_tenant.id
    assert AuditLog.all_objects.filter(
        action="product.created", entity_id=product.id
    ).exists()


def test_update_product_records_diff(active_tenant):
    product = _product(price="100.00")
    product_service.update_product(product.id, {"base_price": Decimal("120.00")})
    log = AuditLog.all_objects.filter(
        action="product.updated", entity_id=product.id
    ).latest("occurred_at")
    assert "base_price" in log.new_value


# --- SKU / barcode uniqueness ---------------------------------------------
def test_sku_unique_per_tenant(active_tenant):
    _product(sku="DUP")
    with pytest.raises(IntegrityError), transaction.atomic():
        _product(sku="DUP")


def test_sku_reusable_after_soft_delete(active_tenant):
    p = _product(sku="REUSE")
    p.delete()  # soft delete
    # Same SKU can now be used again (partial unique excludes deleted rows).
    again = _product(sku="REUSE")
    assert again.pk != p.pk


def test_barcode_partial_unique(active_tenant):
    cat = _category()
    _product(sku="B1", barcode="111", category=cat)
    with pytest.raises(IntegrityError), transaction.atomic():
        _product(sku="B2", barcode="111", category=cat)
    # NULL barcodes are allowed multiple times.
    _product(sku="N1", barcode=None, category=cat)
    _product(sku="N2", barcode=None, category=cat)


def test_sku_not_unique_across_tenants(active_tenant, other_tenant):
    _product(sku="SHARED")
    from shared.tenancy import tenant_context

    with tenant_context(other_tenant.id):
        Product.objects.create(
            category=Category.objects.create(name="Food"),
            name="Other", sku="SHARED", base_price=Decimal("1.00"),
        )  # no error: different tenant


# --- Category tree ---------------------------------------------------------
def test_category_subcategory(active_tenant):
    parent = _category("Beverages")
    child = _category("Cold", parent=parent)
    assert child.parent_id == parent.id
    assert list(parent.children.all()) == [child]


def test_category_cycle_is_rejected(active_tenant):
    parent = _category("A")
    child = _category("B", parent=parent)
    with pytest.raises(CategoryCycle):
        product_service.set_category_parent(parent, child)


# --- Variants / modifiers constraints --------------------------------------
def test_only_one_default_variant(active_tenant):
    product = _product()
    ProductVariant.objects.create(
        product=product, name="Small", sku="V-S", is_default=True
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductVariant.objects.create(
            product=product, name="Large", sku="V-L", is_default=True
        )


def test_modifier_group_min_le_max_enforced(active_tenant):
    with pytest.raises(IntegrityError), transaction.atomic():
        ModifierGroup.objects.create(name="Bad", min_select=3, max_select=1)


# --- Routing inheritance ---------------------------------------------------
def test_routing_inherits_from_category(active_tenant):
    station = KitchenStation.objects.create(code="GRILL", name="Grill")
    # Category routing is a UUID soft-reference (station_id), not an FK.
    category = Category.objects.create(name="Grilled", station_id=station.id)
    product = _product(category=category)  # no station override

    _, resolved = product_service.resolve_routing(product)
    assert resolved == station


def test_routing_product_override_wins(active_tenant):
    cat_station = KitchenStation.objects.create(code="C", name="CatStation")
    prod_station = KitchenStation.objects.create(code="P", name="ProdStation")
    category = Category.objects.create(name="X", station_id=cat_station.id)
    product = _product(category=category)
    product.kitchen_station = prod_station
    product.save()

    _, resolved = product_service.resolve_routing(product)
    assert resolved == prod_station


# --- Soft delete -----------------------------------------------------------
def test_soft_delete_hides_from_default_manager(active_tenant):
    product = _product(sku="SD")
    product.delete()
    assert not Product.objects.filter(id=product.id).exists()
    assert Product.all_objects.filter(id=product.id, is_deleted=True).exists()


# --- Bulk import / export --------------------------------------------------
def test_export_import_roundtrip(active_tenant):
    tax = TaxClass.objects.create(name="GST18", gst_rate=Decimal("18"))
    category = _category("Mains")
    Product.objects.create(
        category=category, tax_class=tax, name="Paneer", sku="P1",
        hsn_code="2106", base_price=Decimal("220.00"),
    )
    Product.objects.create(
        category=category, name="Roti", sku="P2", base_price=Decimal("20.00")
    )

    csv_text = import_export.export_products_csv()
    assert "P1" in csv_text and "P2" in csv_text

    # Soft-delete the originals; SKUs become reusable, so re-import recreates them.
    Product.objects.all().delete()

    report = import_export.import_products_csv(csv_text)
    assert report.created == 2
    assert report.errors == []
    assert Product.objects.filter(sku="P1").exists()


def test_import_reports_unknown_category(active_tenant):
    csv_text = (
        "sku,name,category,type,hsn_code,tax_class,barcode,base_price,currency,is_active\n"
        "X1,Thing,NoSuchCategory,food,,,,"  # missing category
        "50.00,INR,1\n"
    )
    report = import_export.import_products_csv(csv_text)
    assert report.created == 0
    assert len(report.errors) == 1
    assert "category" in report.errors[0]["error"].lower()
