"""Invoice configuration and invoice snapshot models.

InvoiceConfiguration — tenant-scoped (one-per-tenant) receipt presentation settings.
  All static/configurable values that affect how a receipt looks and what it shows.
  Scoped to Tenant via one-to-one; there is no Branch model anymore.

InvoiceSnapshot — immutable per-invoice historical record preserving receipt-time
  data so that changing configuration never mutates old invoices.
"""
from decimal import Decimal

from django.db import models
from django.core.validators import RegexValidator

from shared.tenancy.models import TenantAwareModel


# ── Paper size choices ──────────────────────────────────────────────────────

class PaperSize(models.TextChoices):
    MM_58 = "58mm", "58 mm"
    MM_80 = "80mm", "80 mm"

# ── Currency choices ────────────────────────────────────────────────────────

class CurrencySymbol(models.TextChoices):
    INR = "\u20b9", "\u20b9 (INR)"
    USD = "$", "$ (USD)"
    EUR = "\u20ac", "\u20ac (EUR)"
    GBP = "\u00a3", "\u00a3 (GBP)"

# ── Date format choices ─────────────────────────────────────────────────────

class DateFormat(models.TextChoices):
    DD_MM_YYYY = "d/m/Y", "DD/MM/YYYY"
    DD_MMM_YYYY = "d M Y", "DD Mon YYYY"
    YYYY_MM_DD = "Y-m-d", "YYYY-MM-DD"
    MM_DD_YYYY = "m/d/Y", "MM/DD/YYYY"

# ── Time format choices ─────────────────────────────────────────────────────

class TimeFormat(models.TextChoices):
    H24 = "H:i", "24-hour (14:30)"
    H12 = "h:i A", "12-hour (02:30 PM)"


class InvoiceConfiguration(TenantAwareModel):
    """Per-tenant receipt / invoice presentation configuration.

    One-to-one with Tenant. Created automatically on first access.
    All fields here are STATIC / CONFIGURABLE — they never come from transaction data.
    """

    # ── Business Details ────────────────────────────────────────────────
    restaurant_name = models.CharField(
        max_length=200, blank=True,
        help_text="Display name on receipt (e.g. 'Nextora Bistro')"
    )
    receipt_header = models.CharField(
        max_length=200, blank=True,
        help_text="Receipt header / title (e.g. 'TAX INVOICE')"
    )
    address = models.TextField(
        blank=True,
        help_text="Full restaurant address printed on receipt"
    )
    gstin = models.CharField(
        max_length=15, blank=True,
        validators=[RegexValidator(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$", message="Invalid GSTIN format", code="invalid_gstin")],
        help_text="15-character GSTIN"
    )
    fssai = models.CharField(
        max_length=14, blank=True,
        help_text="14-digit FSSAI license number"
    )
    phone = models.CharField(
        max_length=20, blank=True,
        help_text="Restaurant contact phone"
    )
    email = models.EmailField(
        blank=True,
        help_text="Restaurant contact email"
    )
    website = models.URLField(
        blank=True,
        help_text="Restaurant website URL"
    )

    # ── Receipt Appearance ──────────────────────────────────────────────
    paper_size = models.CharField(
        max_length=4, choices=PaperSize.choices, default=PaperSize.MM_80,
        help_text="Thermal paper width"
    )
    logo = models.ImageField(
        upload_to="logos/",
        blank=True, null=True,
        help_text="Restaurant logo displayed on receipt"
    )
    show_logo = models.BooleanField(
        default=True,
        help_text="Show restaurant logo on receipt"
    )
    custom_header_text = models.TextField(
        blank=True,
        help_text="Custom header text (e.g. 'Home Delivery: +91 98765 43210')"
    )
    custom_footer_text = models.TextField(
        blank=True,
        help_text="Custom footer text (e.g. 'GST on restaurant services')"
    )
    thank_you_message = models.CharField(
        max_length=200,
        default="Thank you for your visit!",
        help_text="Thank-you message at receipt bottom"
    )
    tax_inclusive_message = models.CharField(
        max_length=200, blank=True,
        help_text="Tax-inclusive note (e.g. 'All prices include GST')"
    )
    terms_notes = models.TextField(
        blank=True,
        help_text="Short bill note / terms (e.g. 'No returns after 24 hours')"
    )

    # ── Field Visibility Toggles ────────────────────────────────────────
    show_customer_name = models.BooleanField(default=True)
    show_table_number = models.BooleanField(default=True)
    show_cashier_name = models.BooleanField(default=True)
    show_order_type = models.BooleanField(default=True)
    show_gst_breakdown = models.BooleanField(default=True)
    show_discount = models.BooleanField(default=True)
    show_payment_method = models.BooleanField(default=True)
    show_order_number = models.BooleanField(default=True)
    show_invoice_number = models.BooleanField(default=True)
    show_qr_code = models.BooleanField(default=False)
    show_fssai = models.BooleanField(default=False)
    show_gstin = models.BooleanField(default=True)
    show_service_charge = models.BooleanField(default=True)
    show_item_hsn = models.BooleanField(default=False)
    show_item_discount = models.BooleanField(default=True)

    # ── Number & Date Formatting ────────────────────────────────────────
    currency_symbol = models.CharField(
        max_length=5, choices=CurrencySymbol.choices, default=CurrencySymbol.INR,
        help_text="Currency symbol for amounts"
    )
    date_format = models.CharField(
        max_length=10, choices=DateFormat.choices, default=DateFormat.DD_MMM_YYYY,
        help_text="Date display format on receipt"
    )
    time_format = models.CharField(
        max_length=10, choices=TimeFormat.choices, default=TimeFormat.H24,
        help_text="Time display format on receipt"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "invoice_configuration"
        verbose_name = "Invoice Configuration"
        verbose_name_plural = "Invoice Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="uq_invoice_config__tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"Invoice Config for tenant {self.tenant_id}"


def get_invoice_config(tenant_id) -> InvoiceConfiguration:
    """Get or create an InvoiceConfiguration for the given tenant."""
    config, _ = InvoiceConfiguration.objects.get_or_create(
        tenant_id=tenant_id,
        defaults={},
    )
    return config


# ── InvoiceSnapshot — immutable historical receipt record ──────────────────

class InvoiceSnapshot(TenantAwareModel):
    """Immutable snapshot preserving receipt-time data for a completed invoice.

    Created atomically alongside each Invoice during checkout settlement.
    Once written, this record is NEVER mutated — even if the restaurant updates
    its InvoiceConfiguration or changes its address, FSSAI, etc.
    Historical invoices always render from their snapshot, not live config.
    """
    invoice = models.OneToOneField(
        "ordering.Invoice",
        on_delete=models.CASCADE,
        related_name="snapshot",
        help_text="The invoice this snapshot belongs to",
    )

    # ── Business info at time of invoice ─────────────────────────────────
    business_name = models.CharField(
        max_length=200, blank=True,
        help_text="Restaurant name at invoice time"
    )
    business_address = models.TextField(
        blank=True,
        help_text="Restaurant address at invoice time"
    )
    business_gstin = models.CharField(
        max_length=15, blank=True,
        help_text="Restaurant GSTIN at invoice time"
    )
    business_fssai = models.CharField(
        max_length=14, blank=True,
        help_text="Restaurant FSSAI at invoice time"
    )
    business_phone = models.CharField(
        max_length=20, blank=True,
        help_text="Restaurant phone at invoice time"
    )
    business_email = models.EmailField(
        blank=True,
        help_text="Restaurant email at invoice time"
    )

    # ── Receipt presentation at time of invoice ──────────────────────────
    paper_size = models.CharField(
        max_length=4, choices=PaperSize.choices, default=PaperSize.MM_80
    )
    currency_symbol = models.CharField(
        max_length=5, default="\u20b9"
    )
    custom_footer_text = models.TextField(blank=True)
    thank_you_message = models.CharField(
        max_length=200, blank=True
    )
    tax_inclusive_message = models.CharField(
        max_length=200, blank=True
    )
    terms_notes = models.TextField(blank=True)

    # ── Invoice items at time of invoice (frozen) ────────────────────────
    items_snapshot = models.JSONField(
        default=list, blank=True,
        help_text="Frozen invoice line items at time of issue"
    )

    # ── Totals snapshot (already on Invoice, mirrored for convenience) ───
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_charge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cess = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ── Payment snapshot ─────────────────────────────────────────────────
    payment_methods = models.CharField(max_length=255, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_returned = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ── Metadata ─────────────────────────────────────────────────────────
    customer_name = models.CharField(max_length=160, blank=True)
    table_number = models.CharField(max_length=20, blank=True)
    cashier_name = models.CharField(max_length=160, blank=True)
    order_type_label = models.CharField(max_length=20, blank=True)
    payment_status_label = models.CharField(max_length=20, default="Paid")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "invoice_snapshot"
        verbose_name = "Invoice Snapshot"
        verbose_name_plural = "Invoice Snapshots"

    def __str__(self) -> str:
        invoice_num = getattr(self.invoice, "number", "N/A")
        return f"Snapshot for Invoice {invoice_num}"


def create_invoice_snapshot(invoice) -> InvoiceSnapshot:
    """Create an immutable InvoiceSnapshot from an Invoice and its Order.

    Called during checkout settlement. Attempts to load InvoiceConfiguration
    but gracefully falls back to defaults if none exists.
    This is deliberately NOT inside a savepoint — it MUST succeed alongside
    the invoice creation.
    """
    from contexts.tenants.models import Tenant

    order = invoice.order
    tenant_id = order.tenant_id
    config = None
    try:
        config = get_invoice_config(tenant_id)
    except Exception:
        pass

    # Resolve business info from config or fallback
    business_name = ""
    business_address = ""
    business_gstin = ""
    business_fssai = ""
    business_phone = ""
    business_email = ""
    paper_size = "80mm"
    currency_symbol = "\u20b9"
    thank_you = "Thank you for your visit!"
    footer_text = ""
    tax_msg = ""
    terms = ""

    if config:
        business_name = config.restaurant_name or ""
        business_address = config.address or ""
        business_gstin = config.gstin or ""
        business_fssai = config.fssai or ""
        business_phone = config.phone or ""
        business_email = config.email or ""
        paper_size = config.paper_size
        currency_symbol = config.currency_symbol
        thank_you = config.thank_you_message
        footer_text = config.custom_footer_text
        tax_msg = config.tax_inclusive_message
        terms = config.terms_notes
    else:
        # Fallback to tenant-level data
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            business_name = tenant.name or ""
        except Exception:
            pass

    # Build frozen items snapshot
    items_snapshot = []
    for item in order.items.filter(status="active").select_related("combo").prefetch_related("modifiers"):
        modifiers_list = []
        for mod in item.modifiers.all():
            modifiers_list.append({
                "name": mod.name_snapshot,
                "price_delta": str(mod.price_delta),
                "qty": str(mod.qty),
            })
        items_snapshot.append({
            "name": item.name_snapshot,
            "qty": str(item.qty),
            "unit_price": str(item.unit_price),
            "line_discount": str(item.line_discount),
            "line_subtotal": str(item.line_subtotal),
            "line_total": str(item.line_total),
            "hsn_code": item.hsn_code or "",
            "notes": item.notes or "",
            "modifiers": modifiers_list,
        })

    # Resolve table number
    table_number = ""
    if order.table_id:
        try:
            from contexts.restaurant.models.layout import DiningTable
            tbl = DiningTable.objects.filter(id=order.table_id).first()
            if tbl:
                table_number = tbl.number or ""
        except Exception:
            pass

    # Resolve cashier name
    cashier_name = ""
    if order.created_by:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(id=order.created_by).first()
            if user:
                cashier_name = user.full_name or user.get_username() or ""
        except Exception:
            pass

    # Payment info
    payments = list(order.payments.filter(kind="payment", status="captured"))
    payment_methods = ", ".join(
        p.method.upper() for p in payments
    ) if payments else "CASH"
    total_paid = sum((p.tendered or p.amount) for p in payments) if payments else order.total
    change_returned = max(
        Decimal("0.00"),
        Decimal(str(total_paid)) - order.total
    ) if total_paid else Decimal("0.00")

    snapshot, created = InvoiceSnapshot.objects.get_or_create(
        invoice=invoice,
        defaults={
            "tenant_id": tenant_id,
            "business_name": business_name,
            "business_address": business_address,
            "business_gstin": business_gstin,
            "business_fssai": business_fssai,
            "business_phone": business_phone,
            "business_email": business_email,
            "paper_size": paper_size,
            "currency_symbol": currency_symbol,
            "custom_footer_text": footer_text,
            "thank_you_message": thank_you,
            "tax_inclusive_message": tax_msg,
            "terms_notes": terms,
            "items_snapshot": items_snapshot,
            "subtotal": order.subtotal,
            "discount_amount": order.discount_amount,
            "service_charge_amount": order.service_charge_amount,
            "taxable_amount": order.taxable_amount,
            "cgst": order.cgst,
            "sgst": order.sgst,
            "igst": order.igst,
            "cess": order.cess,
            "tax_amount": order.tax_amount,
            "round_off": order.round_off,
            "total": order.total,
            "payment_methods": payment_methods,
            "amount_paid": Decimal(str(total_paid)),
            "change_returned": change_returned,
            "customer_name": order.customer_name or "",
            "table_number": table_number,
            "cashier_name": cashier_name,
            "order_type_label": order.get_type_display().upper() if hasattr(order, "get_type_display") else str(order.type).upper(),
            "payment_status_label": "Paid",
        },
    )

    return snapshot
