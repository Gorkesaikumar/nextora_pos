from django.contrib import admin

from .models import (
    Category,
    Modifier,
    ModifierGroup,
    Printer,
    Product,
    ProductImage,
    ProductVariant,
    KitchenStation,
    TaxClass,
    Unit,
    ProductComboItem,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

class ProductComboItemInline(admin.TabularInline):
    model = ProductComboItem
    fk_name = "combo"
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "base_price", "is_active", "track_inventory"]
    list_filter = ["type", "is_active"]
    search_fields = ["sku", "name", "barcode", "hsn_code"]
    inlines = [ProductVariantInline, ProductImageInline, ProductComboItemInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "sort_order", "is_active"]
    search_fields = ["name"]


class ModifierInline(admin.TabularInline):
    model = Modifier
    extra = 0


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "min_select", "max_select", "is_required"]
    inlines = [ModifierInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["name", "abbreviation", "is_active"]
    search_fields = ["name", "abbreviation"]


admin.site.register(TaxClass)
admin.site.register(Printer)
admin.site.register(KitchenStation)
