"""Inventory web forms.

Forms cover the four operational surfaces — Suppliers, Inventory Items,
Purchase Orders, and Stock Adjustments. They handle presentation and input
validation only; all business logic (numbering, ledger postings, weighted-cost,
state transitions) lives in the service layer.
"""
from __future__ import annotations

from decimal import Decimal

from django import forms

from contexts.catalog.models.product import Product
from contexts.inventory.models import InventoryItem, Supplier, Warehouse
from contexts.inventory.models.adjustment import AdjustmentReason

# Shared Tailwind classes so every field matches the catalog form styling.
_INPUT = (
    "w-full h-11 px-4 bg-white border border-neutral-300 rounded-xl text-sm "
    "focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all "
    "dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
)
_SELECT = (
    "w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl text-sm "
    "focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all "
    "dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white "
    "appearance-none cursor-pointer"
)
_TEXTAREA = (
    "w-full px-4 py-3 bg-white border border-neutral-300 rounded-xl text-sm "
    "focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 transition-all "
    "dark:bg-neutral-dark-100 dark:border-neutral-dark-300 dark:text-white"
)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name", "code", "contact_person", "phone", "email", "address",
            "gstin", "pan", "credit_days",
            "bank_name", "bank_account_no", "bank_ifsc",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. Fresh Farms Pvt Ltd"}),
            "code": forms.TextInput(attrs={"class": _INPUT, "placeholder": "e.g. SUP-001"}),
            "contact_person": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Contact name"}),
            "phone": forms.TextInput(attrs={"class": _INPUT, "placeholder": "+91 ..."}),
            "email": forms.EmailInput(attrs={"class": _INPUT, "placeholder": "name@example.com"}),
            "address": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2, "placeholder": "Billing / delivery address"}),
            "gstin": forms.TextInput(attrs={"class": _INPUT, "placeholder": "15-digit GSTIN"}),
            "pan": forms.TextInput(attrs={"class": _INPUT, "placeholder": "PAN"}),
            "credit_days": forms.NumberInput(attrs={"class": _INPUT, "min": 0, "placeholder": "0"}),
            "bank_name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Bank name"}),
            "bank_account_no": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Account number"}),
            "bank_ifsc": forms.TextInput(attrs={"class": _INPUT, "placeholder": "IFSC"}),
            "is_active": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
        }


class InventoryItemForm(forms.Form):
    """Provision a stock record for a catalog product in a warehouse.

    This is a plain Form (not a ModelForm) because creating an InventoryItem
    runs through ``item_service.ensure_item`` and an optional opening-balance
    movement — the form only collects and validates the inputs.
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": _SELECT}),
        help_text="Leave blank to use the default warehouse.",
    )
    opening_quantity = forms.DecimalField(
        min_value=0, initial=0, max_digits=14, decimal_places=3,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.001", "placeholder": "0"}),
    )
    average_cost = forms.DecimalField(
        min_value=0, initial=0, max_digits=14, decimal_places=4, required=False,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.0001", "placeholder": "0.00"}),
    )
    minimum_stock = forms.DecimalField(
        min_value=0, initial=0, max_digits=14, decimal_places=3,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.001", "placeholder": "0"}),
    )
    reorder_point = forms.DecimalField(
        min_value=0, initial=0, max_digits=14, decimal_places=3,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.001", "placeholder": "0"}),
    )
    reorder_quantity = forms.DecimalField(
        min_value=0, initial=0, max_digits=14, decimal_places=3,
        widget=forms.NumberInput(attrs={"class": _INPUT, "step": "0.001", "placeholder": "0"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Products without a stock record yet (tenant-scoped by the manager).
        stocked_ids = InventoryItem.objects.values_list("product_id", flat=True)
        self.fields["product"].queryset = (
            Product.objects.filter(is_active=True, track_inventory=True)
            .exclude(id__in=list(stocked_ids))
            .order_by("name")
        )
        self.fields["warehouse"].queryset = Warehouse.objects.filter(is_active=True).order_by("name")


class ReorderLevelsForm(forms.ModelForm):
    """Edit replenishment thresholds for an existing stock record.

    Quantity-on-hand is intentionally not editable here — stock changes flow
    through Stock Adjustments / Purchase receipts so the ledger stays the
    single source of truth.
    """
    class Meta:
        model = InventoryItem
        fields = ["minimum_stock", "reorder_point", "reorder_quantity", "is_active"]
        widgets = {
            "minimum_stock": forms.NumberInput(attrs={"class": _INPUT, "step": "0.001"}),
            "reorder_point": forms.NumberInput(attrs={"class": _INPUT, "step": "0.001"}),
            "reorder_quantity": forms.NumberInput(attrs={"class": _INPUT, "step": "0.001"}),
            "is_active": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded text-neutral-900 border-neutral-300 focus:ring-neutral-900/20 cursor-pointer"
            }),
        }


class PurchaseOrderForm(forms.Form):
    """Header fields for a new purchase order. Line items are parsed separately
    from the POST payload (dynamic rows)."""
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.none(),
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    expected_delivery_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": _INPUT, "type": "date"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2, "placeholder": "Optional notes for the supplier"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True).order_by("name")
        self.fields["warehouse"].queryset = Warehouse.objects.filter(is_active=True).order_by("name")


class StockAdjustmentForm(forms.Form):
    """Header fields for a new stock adjustment. Lines are parsed from POST."""
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    reason = forms.ChoiceField(
        choices=AdjustmentReason.choices,
        widget=forms.Select(attrs={"class": _SELECT}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2, "placeholder": "Reason details / reference"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.filter(is_active=True).order_by("name")


def parse_line_items(post, *, prefix_qty: str = "line_quantity") -> list[dict]:
    """Extract dynamic line rows from a POST payload.

    Rows are submitted as parallel arrays: ``line_item[]``, ``line_quantity[]``,
    and (for purchase orders) ``line_unit_cost[]`` / ``line_tax_rate[]``.
    Returns a list of dicts with raw string values; callers coerce/validate.
    """
    items = post.getlist("line_item")
    quantities = post.getlist(prefix_qty)
    unit_costs = post.getlist("line_unit_cost")
    tax_rates = post.getlist("line_tax_rate")

    rows: list[dict] = []
    for idx, item_id in enumerate(items):
        item_id = (item_id or "").strip()
        qty_raw = (quantities[idx] if idx < len(quantities) else "").strip()
        if not item_id or not qty_raw:
            continue
        row = {"inventory_item_id": item_id, "quantity": qty_raw}
        if idx < len(unit_costs):
            row["unit_cost"] = (unit_costs[idx] or "").strip()
        if idx < len(tax_rates):
            row["tax_rate"] = (tax_rates[idx] or "").strip()
        rows.append(row)
    return rows
