"""Receipt data mapper — transforms Django models into Print Service receipt payload.

This is the single source of truth for receipt data structure.
It maps REAL transaction data from Nextora POS models to the payload format
expected by the Nextora Print Service POST /print endpoint.

Nextora POS is the financial source of truth — no totals are recalculated here.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _resolve_tenant_name(tenant) -> str:
    """Get the business/tenant display name."""
    if tenant is None:
        return "Nextora POS"
    return getattr(tenant, "name", "Nextora POS") or "Nextora POS"


def _resolve_branch_name(order) -> str:
    """Get the store/outlet/branch name for the order."""
    if not getattr(order, 'location_id', None):
        return ""
    try:
        from contexts.restaurant.models import Branch
        branch = Branch.objects.filter(id=getattr(order, 'location_id', None)).first()
        if branch:
            return getattr(branch, "name", "") or ""
    except Exception:
        pass
    return ""


def _resolve_branch_address(order) -> str:
    """Get the branch address."""
    if not getattr(order, 'location_id', None):
        return ""
    try:
        from contexts.restaurant.models import Branch
        branch = Branch.objects.filter(id=getattr(order, 'location_id', None)).first()
        if branch:
            return getattr(branch, "address", "") or ""
    except Exception:
        pass
    return ""


def _resolve_branch_gstin(order) -> str:
    """Get the branch GSTIN."""
    if not getattr(order, 'location_id', None):
        return ""
    try:
        from contexts.restaurant.models import Branch
        branch = Branch.objects.filter(id=getattr(order, 'location_id', None)).first()
        if branch:
            return getattr(branch, "gstin", "") or ""
    except Exception:
        pass
    return ""


def _resolve_branch_phone(order) -> str:
    """Get the branch contact phone."""
    if not getattr(order, 'location_id', None):
        return ""
    try:
        from contexts.restaurant.models import Branch
        branch = Branch.objects.filter(id=getattr(order, 'location_id', None)).first()
        if branch:
            return getattr(branch, "phone", "") or ""
    except Exception:
        pass
    return ""


def _resolve_cashier_name(order) -> str:
    """Resolve cashier/created-by user name."""
    user_id = order.created_by or order.waiter_id
    if user_id:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(id=user_id).first()
            if user:
                return user.full_name or user.get_username() or ""
        except Exception:
            pass
    return "POS Terminal"


def _resolve_table_info(order) -> str:
    """Get the table number/name for the order."""
    if not order.table_id:
        return ""
    try:
        from contexts.restaurant.models.layout import DiningTable
        table = DiningTable.objects.filter(id=order.table_id).first()
        if table:
            return getattr(table, "number", "") or getattr(table, "name", "") or ""
    except Exception:
        pass
    return ""


def _format_currency(value: Decimal, currency: str = "INR") -> str:
    """Format a decimal as a currency string."""
    return f"{value:.2f}"


def _load_invoice_config(tenant_id):
    """Load InvoiceConfiguration for a tenant, returning a dict or None."""
    try:
        from contexts.ordering.models.invoice_config import get_invoice_config
        cfg = get_invoice_config(tenant_id)
        return cfg
    except Exception:
        return None


def build_live_receipt_context(
    order,
    invoice,
    *,
    copy_type: str = "customer",
    is_reprint: bool = False,
    paper_width: str = "80mm",
) -> Dict[str, Any]:
    """Build the exact context required for the invoice_config_preview.html template."""
    tenant = getattr(order, "tenant", None)
    tenant_id = order.tenant_id if order else None
    
    # Load InvoiceConfiguration if available
    config = _load_invoice_config(tenant_id) if tenant_id else None
    
    # Resolve business info from config (with fallbacks)
    if config:
        business_name = config.restaurant_name or _resolve_tenant_name(tenant)
        business_address = config.address or _resolve_branch_address(order)
        business_gstin = config.gstin or _resolve_branch_gstin(order)
        business_fssai = config.fssai or ""
        business_phone = config.phone or _resolve_branch_phone(order)
        config_paper_width = config.paper_size or paper_width
        currency_sym = config.currency_symbol or ""
        thank_you = config.thank_you_message or "THANK YOU FOR YOUR VISIT!"
        footer_text = config.custom_footer_text or ""
        header_text = config.custom_header_text or ""
        logo_url = config.logo.url if config.show_logo and getattr(config.logo, 'name', None) else ""
    else:
        business_name = _resolve_tenant_name(tenant)
        business_address = _resolve_branch_address(order)
        business_gstin = _resolve_branch_gstin(order)
        business_fssai = ""
        business_phone = _resolve_branch_phone(order)
        config_paper_width = paper_width
        currency_sym = ""
        thank_you = "THANK YOU FOR YOUR VISIT!"
        footer_text = ""
        header_text = ""
        logo_url = ""

    branch_name = _resolve_branch_name(order)
    cashier_name = _resolve_cashier_name(order)
    table_info = _resolve_table_info(order)

    now = getattr(invoice, "issued_at", timezone.now())
    now_str = now.strftime("%d %b %Y") if isinstance(now, datetime) else str(now)
    time_str = now.strftime("%H:%M") if isinstance(now, datetime) else ""

    # ── Items ─────────────────────────────────────────────────────────────
    items_data: List[Dict[str, Any]] = []
    active_items = order.items.filter(status="active").select_related("combo").prefetch_related("modifiers")

    for item in active_items:
        modifiers_list: List[Dict[str, str]] = []
        for mod in item.modifiers.all():
            mod_entry: Dict[str, Any] = {
                "name": mod.name_snapshot,
            }
            if mod.price_delta and mod.price_delta > 0:
                mod_entry["price_delta"] = str(mod.price_delta)
                mod_entry["qty"] = "1"
            modifiers_list.append(mod_entry)

        items_data.append({
            "name": item.name_snapshot,
            "qty": str(float(item.qty)).rstrip('0').rstrip('.') if item.qty % 1 == 0 else str(float(item.qty)),
            "unit_price": str(item.unit_price),
            "line_total": str(item.line_total),
            "line_discount": "0.00",
            "modifiers": modifiers_list,
            "hsn_code": item.hsn_code or "",
            "notes": item.notes or "",
        })

    # ── Payment info ──────────────────────────────────────────────────────
    payments = list(order.payments.filter(kind="payment", status="captured"))
    payment_methods = ", ".join(p.get_method_display().upper() if hasattr(p, "get_method_display") else p.method.upper() for p in payments)
    total_paid = sum((p.tendered or p.amount) for p in payments) if payments else order.total
    change_returned = max(Decimal("0.00"), Decimal(str(total_paid)) - order.total) if total_paid else Decimal("0.00")

    context = {
        "invoice_number": invoice.number,
        "order_number": order.order_number or "",
        "table_number": table_info,
        "customer_name": order.customer_name or "",
        "cashier_name": cashier_name,
        "order_type": order.get_type_display().upper() if hasattr(order, "get_type_display") else str(order.type).upper(),
        "date": now_str,
        "time": time_str,
        "items": items_data,
        "subtotal": str(order.subtotal),
        "discount_amount": str(order.discount_amount),
        "service_charge_amount": str(order.service_charge_amount),
        "taxable_amount": str(order.taxable_amount),
        "cgst": str(order.cgst),
        "sgst": str(order.sgst),
        "igst": str(order.igst),
        "cess": str(order.cess),
        "tax_amount": str(order.tax_amount),
        "round_off": str(order.round_off),
        "total": str(order.total),
        "payment_method": payment_methods,
        "amount_paid": str(total_paid),
        "change_returned": str(change_returned),
        "payment_status": "Paid",
        "is_preview": False,
        "is_reprint": is_reprint,
        
        "config": config,
        "business_name": business_name,
        "business_address": business_address,
        "business_gstin": business_gstin,
        "business_fssai": business_fssai,
        "business_phone": business_phone,
        "logo_url": logo_url,
        "custom_header_text": header_text,
        "custom_footer_text": footer_text,
        "thank_you_message": thank_you,
        "paper_width": config_paper_width,
        "currency_symbol": currency_sym,
    }
    
    if copy_type == "restaurant":
        context["is_restaurant_copy"] = True
        context["thank_you_message"] = "ACCOUNTING & AUDIT RECORD"

    return context


def render_receipt_html(
    order,
    invoice,
    *,
    copy_type: str = "customer",
    is_reprint: bool = False,
    paper_width: str = "80mm",
) -> str:
    """Render the exact same HTML template used for preview but with real data."""
    from django.template.loader import render_to_string
    context = build_live_receipt_context(
        order, invoice, copy_type=copy_type, is_reprint=is_reprint, paper_width=paper_width
    )
    # The preview uses this exact template!
    return render_to_string("ordering/partials/invoice_config_preview.html", context)


def build_receipt_payload(
    order,
    invoice,
    *,
    copy_type: str = "customer",
    is_reprint: bool = False,
    paper_width: str = "80mm",
) -> Dict[str, Any]:
    """Map real transaction and configuration data into Print Service JSON schema.

    Ensures 100% fidelity between what is configured in InvoiceConfiguration / InvoiceSnapshot
    and what RestaurantTemplate renders on physical thermal receipts.
    """
    tenant = getattr(order, "tenant", None)
    tenant_id = order.tenant_id if order else None
    config = _load_invoice_config(tenant_id) if tenant_id else None

    # Check for immutable snapshot first (for completed invoices)
    snapshot = getattr(invoice, "snapshot", None) if invoice else None

    # ── Resolve Business & Appearance Details ─────────────────────────────
    if snapshot and snapshot.business_name:
        business_name = snapshot.business_name
        business_address = snapshot.business_address
        business_gstin = snapshot.business_gstin
        business_phone = snapshot.business_phone
        paper_size_str = snapshot.paper_size
        thank_you = snapshot.thank_you_message
        footer_text = snapshot.custom_footer_text
        terms = snapshot.terms_notes
    elif config:
        business_name = config.restaurant_name or _resolve_tenant_name(tenant)
        business_address = config.address or _resolve_branch_address(order)
        business_gstin = config.gstin or _resolve_branch_gstin(order)
        business_phone = config.phone or _resolve_branch_phone(order)
        paper_size_str = config.paper_size or paper_width
        thank_you = config.thank_you_message or "Thank you for your visit!"
        footer_text = config.custom_footer_text or ""
        terms = config.terms_notes or ""
    else:
        business_name = _resolve_tenant_name(tenant)
        business_address = _resolve_branch_address(order)
        business_gstin = _resolve_branch_gstin(order)
        business_phone = _resolve_branch_phone(order)
        paper_size_str = paper_width
        thank_you = "Thank you for your visit!"
        footer_text = ""
        terms = ""

    # Check show toggles if config exists
    show_logo = config.show_logo if config else True
    show_invoice_num = config.show_invoice_number if config else True
    show_order_num = config.show_order_number if config else True
    show_customer = config.show_customer_name if config else True
    show_table = config.show_table_number if config else True
    show_cashier = config.show_cashier_name if config else True
    show_order_type = config.show_order_type if config else True
    show_discount = config.show_discount if config else True
    show_gst_breakdown = config.show_gst_breakdown if config else True
    show_payment_method = config.show_payment_method if config else True
    show_qr = config.show_qr_code if config else False

    # Header text / Subtitle
    subtitle = config.custom_header_text if config else ""

    # Logo URL or path
    logo_val = None
    if show_logo and config and getattr(config.logo, 'name', None):
        try:
            logo_val = config.logo.path
        except Exception:
            logo_val = config.logo.url

    # Timestamps
    now = getattr(invoice, "issued_at", timezone.now()) if invoice else timezone.now()
    now_str = now.strftime("%d %b %Y") if isinstance(now, datetime) else str(now)
    time_str = now.strftime("%H:%M") if isinstance(now, datetime) else ""

    # Items
    items_list: List[Dict[str, Any]] = []
    if snapshot and snapshot.items_snapshot:
        for snap_item in snapshot.items_snapshot:
            items_list.append({
                "name": snap_item.get("name", ""),
                "qty": snap_item.get("qty", 1),
                "price": snap_item.get("unit_price", 0),
                "amount": snap_item.get("line_total", 0),
            })
    else:
        for item in order.items.filter(status="active").select_related("combo").prefetch_related("modifiers"):
            items_list.append({
                "name": item.name_snapshot,
                "qty": str(float(item.qty)).rstrip('0').rstrip('.') if item.qty % 1 == 0 else str(float(item.qty)),
                "price": str(item.unit_price),
                "amount": str(item.line_total),
            })

    # Payment Methods
    payments = list(order.payments.filter(kind="payment", status="captured"))
    payment_methods = ", ".join(p.get_method_display().upper() if hasattr(p, "get_method_display") else p.method.upper() for p in payments)
    if not payment_methods and snapshot and snapshot.payment_methods:
        payment_methods = snapshot.payment_methods

    # Paper width mm
    paper_width_mm = 80 if "80" in str(paper_size_str) else 58

    # Assemble exact structure expected by cls.build_receipt_object (RestaurantTemplate)
    restaurant_dict = {
        "name": business_name if business_name else " ",  # Space prevents fallback to default
        "subtitle": subtitle,
        "address": business_address,
        "phone": business_phone,
        "gst": business_gstin if (show_gst_breakdown or (config and config.show_gstin)) else "",
        "logo": logo_val,
    }

    invoice_dict = {
        "number": (invoice.number if show_invoice_num else "") if invoice else "",
        "date": now_str,
        "time": time_str,
    }

    footer_dict = {
        "thank_you": thank_you if thank_you else "",
        "visit_again": "Visit Again" if thank_you else "",
        "return_policy": terms,
        "website": config.website if config else "",
        "custom_text": footer_text,
    }

    payload = {
        "restaurant": restaurant_dict,
        "invoice": invoice_dict,
        "order_id": order.order_number if show_order_num else "",
        "cashier": _resolve_cashier_name(order) if show_cashier else "",
        "customer": order.customer_name if show_customer else "",
        "table": _resolve_table_info(order) if show_table else "",
        "order_type": (order.get_type_display().upper() if hasattr(order, "get_type_display") else str(order.type).upper()) if show_order_type else "",
        "items": items_list,
        "subtotal": str(order.subtotal),
        "discount": str(order.discount_amount) if show_discount else "0.00",
        "gst": str(order.tax_amount) if show_gst_breakdown else "0.00",
        "tax": str(order.tax_amount) if show_gst_breakdown else "0.00",
        "grand_total": str(order.total),
        "total": str(order.total),
        "payment_method": payment_methods if show_payment_method else "",
        "footer": footer_dict,
        "paper_width_mm": paper_width_mm,
        "template": "restaurant",
        "receipt_type": "Customer Receipt" if copy_type == "customer" else "RESTAURANT COPY",
    }

    if show_qr and config:
        # If QR code is enabled, pass simple reference string or URL if available
        payload["qrcode"] = f"INV:{invoice.number}" if invoice and hasattr(invoice, 'number') else f"ORD:{order.order_number}"

    return payload


def build_diagnostic_payload(
    printer_name: str,
    connection_type: str = "",
    paper_width_mm: int = 58,
) -> Dict[str, Any]:
    """Build a diagnostic test print payload.

    This is sent as the receipt body for a test print.
    The Print Service will render it as a diagnostic receipt.
    """
    now = timezone.now()
    return {
        "diagnostic": True,
        "printer_name": printer_name,
        "connection_type": connection_type,
        "paper_width_mm": paper_width_mm,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
