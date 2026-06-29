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
            'is_active', 'track_inventory'
        ]
        widgets = {
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
