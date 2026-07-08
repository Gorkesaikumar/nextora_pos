from django import forms
from contexts.catalog.models.product import Product
from contexts.catalog.models.category import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white',
                'placeholder': 'e.g. Beverages'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white',
                'rows': 2,
                'placeholder': 'Optional description...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        if name:
            from django.utils.text import slugify
            from shared.tenancy.context import get_current_tenant
            slug = slugify(name)
            tenant_id = get_current_tenant()
            qs = Category.objects.filter(tenant_id=tenant_id, slug=slug, is_deleted=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('name', f'A category with the name "{name}" already exists.')
        return cleaned_data

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'category', 'type', 
            'base_price', 'currency', 'description', 
            'is_active', 'track_inventory', 'modifier_groups'
        ]
        widgets = {
            'modifier_groups': forms.CheckboxSelectMultiple(attrs={
                'class': 'w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white', 
                'placeholder': 'e.g. Margherita Pizza'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white', 
                'placeholder': 'e.g. PIZ-MAR-001'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer'
            }),
            'type': forms.Select(attrs={
                'class': 'w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer'
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'w-full h-11 pl-10 pr-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white', 
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'currency': forms.TextInput(attrs={
                'class': 'w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white',
                'readonly': 'readonly'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white', 
                'rows': 3, 
                'placeholder': 'Optional description...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer'
            }),
            'track_inventory': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('currency'):
            self.initial['currency'] = 'INR'

        # Category queryset is tenant-scoped by the TenantSoftDeleteManager.
        # On edit, include the instance's existing category so an entry that was
        # later deactivated does not block a legitimate update with
        # "Select a valid choice".
        active = Category.objects.filter(is_active=True)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk and instance.category_id:
            from django.db.models import Q
            active = (
                Category.objects.filter(
                    Q(is_active=True) | Q(pk=instance.category_id)
                )
            )
        self.fields['category'].queryset = active.order_by('name')
        self.fields['modifier_groups'].queryset = ModifierGroup.objects.filter(
            is_active=True, is_deleted=False
        ).order_by('sort_order', 'name')
        self.fields['modifier_groups'].required = False


from contexts.catalog.models.modifier import ModifierGroup, Modifier


class ModifierGroupForm(forms.ModelForm):
    class Meta:
        model = ModifierGroup
        fields = [
            "name", "internal_code", "display_name", "description",
            "selection_type", "min_select", "max_select", "is_required",
            "display_style", "expand_by_default", "sort_order",
            "print_on_invoice", "print_on_restaurant_copy", "print_on_kitchen_ticket",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. Choice of Crust, Add-Ons"
            }),
            "internal_code": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. GRP-CRUST-01"
            }),
            "display_name": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. Select your crust (optional override)"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "rows": 2,
                "placeholder": "Customer-facing hint..."
            }),
            "selection_type": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "min_select": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
            }),
            "max_select": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
            }),
            "display_style": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "sort_order": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
            }),
            "is_required": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "expand_by_default": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "print_on_invoice": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "print_on_restaurant_copy": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "print_on_kitchen_ticket": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_select = cleaned_data.get("min_select", 0)
        max_select = cleaned_data.get("max_select", 1)
        is_required = cleaned_data.get("is_required", False)
        selection_type = cleaned_data.get("selection_type", "multiple")

        if max_select < min_select:
            self.add_error("max_select", "Maximum selection cannot be less than minimum selection.")
        if is_required and min_select < 1:
            cleaned_data["min_select"] = 1
        if selection_type == "single" and max_select > 1:
            cleaned_data["max_select"] = 1
        return cleaned_data


class ModifierForm(forms.ModelForm):
    class Meta:
        model = Modifier
        fields = [
            "name", "description", "sku", "price_delta", "price_type",
            "inventory_item", "quantity_consumed", "color_code",
            "is_default", "is_taxable", "is_active", "sort_order"
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. Extra Cheese"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "rows": 2,
                "placeholder": "Optional description..."
            }),
            "sku": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. MOD-CHS-001"
            }),
            "price_delta": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "step": "0.01"
            }),
            "price_type": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "inventory_item": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "quantity_consumed": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "step": "0.001"
            }),
            "color_code": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. #3B82F6"
            }),
            "sort_order": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
            }),
            "is_default": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "is_taxable": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
        }

from contexts.catalog.models.combo import ComboOffer

class ComboOfferForm(forms.ModelForm):
    class Meta:
        model = ComboOffer
        fields = [
            "name", "description", "status", "offer_type", "discount_value",
            "min_order_value", "min_cart_items", "customer_eligibility",
            "usage_limit_type", "usage_limit_value"
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "placeholder": "e.g. Family Meal Deal"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "rows": 3,
                "placeholder": "Describe what is included..."
            }),
            "status": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "offer_type": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "discount_value": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "step": "0.01"
            }),
            "min_order_value": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
                "step": "0.01"
            }),
            "min_cart_items": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
            }),
            "customer_eligibility": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "usage_limit_type": forms.Select(attrs={
                "class": "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white appearance-none cursor-pointer"
            }),
            "usage_limit_value": forms.NumberInput(attrs={
                "class": "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white",
            }),
        }
