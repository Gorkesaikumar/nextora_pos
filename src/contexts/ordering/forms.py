"""Forms for the ordering / POS context — Invoice Configuration."""
from django import forms

from contexts.ordering.models.invoice_config import (
    InvoiceConfiguration,
    PaperSize,
    CurrencySymbol,
    DateFormat,
    TimeFormat,
)


class InvoiceConfigurationForm(forms.ModelForm):
    """Form for configuring receipt/invoice presentation settings."""

    class Meta:
        model = InvoiceConfiguration
        fields = [
            # Business Details
            "restaurant_name",
            "receipt_header",
            "address",
            "gstin",
            "fssai",
            "phone",
            "email",
            "website",
            # Receipt Appearance
            "paper_size",
            "logo",
            "show_logo",
            "custom_header_text",
            "custom_footer_text",
            "thank_you_message",
            "tax_inclusive_message",
            "terms_notes",
            # Field Visibility
            "show_customer_name",
            "show_table_number",
            "show_cashier_name",
            "show_order_type",
            "show_gst_breakdown",
            "show_discount",
            "show_payment_method",
            "show_order_number",
            "show_invoice_number",
            "show_qr_code",
            "show_fssai",
            "show_gstin",
            "show_service_charge",
            "show_item_hsn",
            "show_item_discount",
            # Number & Date Formatting
            "currency_symbol",
            "date_format",
            "time_format",
        ]
        widgets = {
            # Business Details
            "restaurant_name": forms.TextInput(attrs={
                "class": "input", "placeholder": "e.g. Nextora Bistro",
                "x-model": "config.restaurant_name",
            }),
            "receipt_header": forms.TextInput(attrs={
                "class": "input", "placeholder": "e.g. TAX INVOICE / BILL",
                "x-model": "config.receipt_header",
            }),
            "address": forms.Textarea(attrs={
                "class": "input", "rows": 3, "placeholder": "Full restaurant address",
                "x-model": "config.address",
            }),
            "gstin": forms.TextInput(attrs={
                "class": "input", "placeholder": "27ABCDE1234F1Z5",
                "maxlength": "15",
                "x-model": "config.gstin",
            }),
            "fssai": forms.TextInput(attrs={
                "class": "input", "placeholder": "12345678901234",
                "maxlength": "14",
                "x-model": "config.fssai",
            }),
            "phone": forms.TextInput(attrs={
                "class": "input", "placeholder": "+91 98765 43210",
                "x-model": "config.phone",
            }),
            "email": forms.EmailInput(attrs={
                "class": "input", "placeholder": "hello@nextora.app",
                "x-model": "config.email",
            }),
            "website": forms.URLInput(attrs={
                "class": "input", "placeholder": "https://nextora.app",
                "x-model": "config.website",
            }),
            # Receipt Appearance
            "paper_size": forms.Select(attrs={
                "class": "select", "x-model": "config.paper_size",
                "@change": "updatePreview()",
            }),
            "logo": forms.ClearableFileInput(attrs={
                "class": "input text-sm py-1.5",
                "accept": "image/png,image/jpeg,image/webp",
            }),
            "show_logo": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_logo",
            }),
            "custom_header_text": forms.Textarea(attrs={
                "class": "input", "rows": 2, "placeholder": "Custom text above items...",
                "x-model": "config.custom_header_text",
            }),
            "custom_footer_text": forms.Textarea(attrs={
                "class": "input", "rows": 2, "placeholder": "Custom text below payment info...",
                "x-model": "config.custom_footer_text",
            }),
            "thank_you_message": forms.TextInput(attrs={
                "class": "input", "placeholder": "Thank you for your visit!",
                "x-model": "config.thank_you_message",
            }),
            "tax_inclusive_message": forms.TextInput(attrs={
                "class": "input", "placeholder": "All prices include GST",
                "x-model": "config.tax_inclusive_message",
            }),
            "terms_notes": forms.Textarea(attrs={
                "class": "input", "rows": 2, "placeholder": "Terms / notes...",
                "x-model": "config.terms_notes",
            }),
            # Toggle switches for visibility
            "show_customer_name": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_customer_name",
                "@change": "updatePreview()",
            }),
            "show_table_number": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_table_number",
                "@change": "updatePreview()",
            }),
            "show_cashier_name": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_cashier_name",
                "@change": "updatePreview()",
            }),
            "show_order_type": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_order_type",
                "@change": "updatePreview()",
            }),
            "show_gst_breakdown": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_gst_breakdown",
                "@change": "updatePreview()",
            }),
            "show_discount": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_discount",
                "@change": "updatePreview()",
            }),
            "show_payment_method": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_payment_method",
                "@change": "updatePreview()",
            }),
            "show_order_number": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_order_number",
                "@change": "updatePreview()",
            }),
            "show_invoice_number": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_invoice_number",
                "@change": "updatePreview()",
            }),
            "show_qr_code": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_qr_code",
                "@change": "updatePreview()",
            }),
            "show_fssai": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_fssai",
                "@change": "updatePreview()",
            }),
            "show_gstin": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_gstin",
                "@change": "updatePreview()",
            }),
            "show_service_charge": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_service_charge",
                "@change": "updatePreview()",
            }),
            "show_item_hsn": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_item_hsn",
                "@change": "updatePreview()",
            }),
            "show_item_discount": forms.CheckboxInput(attrs={
                "class": "toggle", "x-model": "config.show_item_discount",
                "@change": "updatePreview()",
            }),
            # Formatting
            "currency_symbol": forms.Select(attrs={
                "class": "select", "x-model": "config.currency_symbol",
                "@change": "updatePreview()",
            }),
            "date_format": forms.Select(attrs={
                "class": "select", "x-model": "config.date_format",
                "@change": "updatePreview()",
            }),
            "time_format": forms.Select(attrs={
                "class": "select", "x-model": "config.time_format",
                "@change": "updatePreview()",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.tenant_id = kwargs.pop("tenant_id", None)
        super().__init__(*args, **kwargs)
        # Make all fields optional since defaults exist
        for field_name in self.fields:
            self.fields[field_name].required = False

    def clean_gstin(self):
        val = self.cleaned_data.get("gstin", "")
        if val:
            val = val.upper().strip()
        return val

    def clean_fssai(self):
        val = self.cleaned_data.get("fssai", "")
        if val:
            val = val.strip()
        return val
