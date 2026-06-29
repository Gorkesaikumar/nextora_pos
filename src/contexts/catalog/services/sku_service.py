"""Services for generating SKUs, Barcodes, and mapping Inventory."""

import random
import string
from django.db import transaction

from contexts.catalog.models import Product, ProductVariant

def generate_sku(prefix: str = "PRD") -> str:
    """Generate a unique SKU."""
    while True:
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        sku = f"{prefix}-{random_suffix}"
        if not Product.objects.filter(sku=sku).exists() and not ProductVariant.objects.filter(sku=sku).exists():
            return sku

def generate_barcode() -> str:
    """Generate a unique 13-digit EAN-like barcode."""
    while True:
        barcode = "".join(random.choices(string.digits, k=13))
        if not Product.objects.filter(barcode=barcode).exists() and not ProductVariant.objects.filter(barcode=barcode).exists():
            return barcode

@transaction.atomic
def auto_assign_sku_and_barcode(product: Product) -> Product:
    """Automatically assign SKU and barcode if they are missing."""
    changed = False
    if not product.sku:
        prefix = product.category.name[:3].upper() if product.category else "PRD"
        product.sku = generate_sku(prefix)
        changed = True
        
    if not product.barcode:
        product.barcode = generate_barcode()
        changed = True
        
    if changed:
        product.save(update_fields=["sku", "barcode"])
        
    return product

def map_product_to_inventory(product: Product, inventory_item_id: str) -> Product:
    """Map a product to a specific inventory item ID."""
    product.inventory_item_id = inventory_item_id
    product.track_inventory = True
    product.save(update_fields=["inventory_item_id", "track_inventory"])
    return product
