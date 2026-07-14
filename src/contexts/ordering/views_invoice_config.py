"""Views for Invoice Configuration management and receipt preview."""
import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin
from contexts.ordering.forms import InvoiceConfigurationForm
from contexts.ordering.models.invoice_config import (
    InvoiceConfiguration,
    InvoiceSnapshot,
    get_invoice_config,
)
from contexts.ordering.models.invoice import Invoice
from contexts.ordering.models.order import Order
from contexts.ordering.domain.enums import OrderStatus
from contexts.ordering.services.print_service_client import PrintServiceClient
from contexts.ordering.services.printing import dispatch_to_print_service


# ── Standalone preview data builder ─────────────────────────────────────────

def _build_demo_preview_data(config) -> dict:
    """Build demo transaction data for the live receipt preview.

    Uses realistic but clearly preview/demo data. NEVER saves this as a real invoice.
    This is a standalone function shared by both InvoiceConfigurationView and
    InvoiceConfigurationPreviewView.
    """
    return {
        "invoice_number": "INV-250714-0001",
        "order_number": "ORD-250714-0001",
        "table_number": "T7",
        "customer_name": "Rahul Sharma",
        "cashier_name": "Asha Singh",
        "order_type": "DINE-IN",
        "date": "14 Jul 2026",
        "time": "14:30",
        "items": [
            {
                "name": "Mutton Biryani",
                "qty": "2",
                "unit_price": "250.00",
                "line_discount": "0.00",
                "line_total": "500.00",
                "hsn_code": "2106",
                "modifiers": [],
                "notes": "",
            },
            {
                "name": "Paneer Butter Masala",
                "qty": "1",
                "unit_price": "350.00",
                "line_discount": "0.00",
                "line_total": "350.00",
                "hsn_code": "2106",
                "modifiers": [
                    {"name": "Extra Cheese", "price_delta": "40.00", "qty": "1"},
                ],
                "notes": "",
            },
            {
                "name": "Garlic Naan",
                "qty": "3",
                "unit_price": "70.00",
                "line_discount": "50.00",
                "line_total": "160.00",
                "hsn_code": "1905",
                "modifiers": [],
                "notes": "",
            },
        ],
        "subtotal": "890.00",
        "discount_amount": "50.00",
        "service_charge_amount": "44.50",
        "taxable_amount": "884.50",
        "cgst": "22.11",
        "sgst": "22.11",
        "igst": "0.00",
        "cess": "0.00",
        "tax_amount": "44.22",
        "round_off": "0.28",
        "total": "979.00",
        "payment_method": "CASH",
        "amount_paid": "1000.00",
        "change_returned": "21.00",
        "payment_status": "Paid",
        "is_preview": True,
    }


def _serialize_config_for_alpine(config) -> dict:
    """Serialize InvoiceConfiguration into a JSON-safe dict for Alpine.js."""
    try:
        logo_url = config.logo.url if config.logo else ""
    except Exception:
        logo_url = ""
    return {
        "logo_url": logo_url,
        "restaurant_name": config.restaurant_name or "",
        "receipt_header": config.receipt_header or "TAX INVOICE",
        "address": config.address or "",
        "gstin": config.gstin or "",
        "fssai": config.fssai or "",
        "phone": config.phone or "",
        "email": config.email or "",
        "website": config.website or "",
        "paper_size": config.paper_size or "80mm",
        "show_logo": config.show_logo,
        "custom_header_text": config.custom_header_text or "",
        "custom_footer_text": config.custom_footer_text or "",
        "thank_you_message": config.thank_you_message or "Thank you for your visit!",
        "tax_inclusive_message": config.tax_inclusive_message or "",
        "terms_notes": config.terms_notes or "",
        "show_customer_name": config.show_customer_name,
        "show_table_number": config.show_table_number,
        "show_cashier_name": config.show_cashier_name,
        "show_order_type": config.show_order_type,
        "show_gst_breakdown": config.show_gst_breakdown,
        "show_discount": config.show_discount,
        "show_payment_method": config.show_payment_method,
        "show_order_number": config.show_order_number,
        "show_invoice_number": config.show_invoice_number,
        "show_qr_code": config.show_qr_code,
        "show_fssai": config.show_fssai,
        "show_gstin": config.show_gstin,
        "show_service_charge": config.show_service_charge,
        "show_item_hsn": config.show_item_hsn,
        "show_item_discount": config.show_item_discount,
        "currency_symbol": config.currency_symbol or "₹",
        "date_format": config.date_format or "d M Y",
        "time_format": config.time_format or "H:i",
    }


class InvoiceConfigurationView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    """Invoice Configuration dashboard page with live receipt preview.

    Renders a two-column layout:
      - Left: configuration form (business details, appearance, visibility toggles)
      - Right: live thermal receipt preview that updates in real-time
    """
    permission_required = "orders.update"
    template_name = "ordering/invoice_configuration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = self.request.tenant_id

        # Get or create config
        config = get_invoice_config(tenant_id)

        # Build form with current values
        form = InvoiceConfigurationForm(
            instance=config,
            tenant_id=tenant_id,
        )

        # Serialize config as JSON for Alpine.js binding (preview reactivity)
        config_json = _serialize_config_for_alpine(config)

        # Build preview context data (demo transaction data for preview only)
        preview_data = _build_demo_preview_data(config)

        context.update({
            "form": form,
            "config_instance": config,
            "config_json": config_json,
            "config_json_str": json.dumps(config_json),
            "preview_json": preview_data,
            "preview_json_str": json.dumps(preview_data),
            "preview_data": preview_data,
            "page_title": "Invoice Configuration",
            "page_subtitle": "Configure receipt appearance, business details, and field visibility.",
        })
        return context


class InvoiceConfigurationSaveView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """Save Invoice Configuration changes via AJAX or form POST."""
    permission_required = "orders.update"

    def post(self, request, *args, **kwargs):
        tenant_id = request.tenant_id
        config = get_invoice_config(tenant_id)
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        # Handle JSON save from saveConfig()
        if request.content_type == "application/json":
            import json
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
            
            form = InvoiceConfigurationForm(
                data=data,
                instance=config,
                tenant_id=tenant_id,
            )
            if form.is_valid():
                saved_config = form.save()
                return JsonResponse({
                    "success": True,
                    "message": "Invoice configuration saved successfully.",
                    "config": _serialize_config_for_alpine(saved_config),
                })
            else:
                errors = {field: [str(e) for e in err_list] for field, err_list in form.errors.items()}
                return JsonResponse({"success": False, "error": "Validation failed.", "errors": errors}, status=400)

        # Handle Logo upload from handleLogoUpload()
        elif "logo" in request.FILES:
            config.logo = request.FILES["logo"]
            config.save()
            return JsonResponse({
                "success": True,
                "message": "Logo uploaded successfully.",
                "config": _serialize_config_for_alpine(config),
            })

        # Fallback for standard POST
        form = InvoiceConfigurationForm(
            data=request.POST,
            files=request.FILES,
            instance=config,
            tenant_id=tenant_id,
        )

        if form.is_valid():
            saved_config = form.save()
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": "Invoice configuration saved successfully.",
                    "config": _serialize_config_for_alpine(saved_config),
                })
            from django.contrib import messages
            messages.success(request, "Invoice configuration saved successfully.")
        else:
            if is_ajax:
                errors = {field: [str(e) for e in err_list] for field, err_list in form.errors.items()}
                return JsonResponse({"success": False, "error": "Validation failed.", "errors": errors}, status=400)
            from django.contrib import messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect("ordering:invoice_config")


class InvoiceConfigurationResetView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """Reset Invoice Configuration to factory defaults."""
    permission_required = "orders.update"

    def post(self, request, *args, **kwargs):
        tenant_id = request.tenant_id
        config = get_invoice_config(tenant_id)

        # Reset all configurable fields to defaults
        from contexts.ordering.models.invoice_config import InvoiceConfiguration as IC
        _reset_fields = {f.name for f in IC._meta.get_fields() 
                        if hasattr(f, "default") and f.default is not None
                        and f.name not in ("id", "tenant", "tenant_id", 
                                           "created_at", "updated_at",
                                           "created_by", "updated_by",
                                           "is_deleted", "deleted_at")}
        for field_name in _reset_fields:
            try:
                field = IC._meta.get_field(field_name)
                setattr(config, field_name, field.default)
            except Exception:
                pass

        config.save()

        return JsonResponse({
            "success": True,
            "config": _serialize_config_for_alpine(config),
        })


class InvoiceConfigurationTestPrintView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """Send a test print to the configured printer via Print Service."""
    permission_required = "orders.update"

    def post(self, request, *args, **kwargs):
        from contexts.ordering.services.print_service_client import PrintServiceClient
        from contexts.ordering.models.pos_config import POSPrinterConfig

        # Get the configured printer
        printer_name = ""
        try:
            config = POSPrinterConfig.objects.filter(
                tenant_id=request.tenant_id,
                is_active=True,
            ).first()
            if config and config.printer_name:
                printer_name = config.printer_name
        except Exception:
            pass

        if not printer_name:
            return JsonResponse({
                "success": False,
                "error": "No receipt printer configured. Please select a printer in Printer Settings first.",
            }, status=400)

        # Build a test payload
        tenant_id = request.tenant_id
        invoice_config = get_invoice_config(tenant_id)

        # Check show toggles
        show_logo = invoice_config.show_logo
        show_invoice_num = invoice_config.show_invoice_number
        show_gst_breakdown = invoice_config.show_gst_breakdown
        show_discount = invoice_config.show_discount
        show_payment_method = invoice_config.show_payment_method

        logo_val = None
        if show_logo and getattr(invoice_config.logo, 'name', None):
            try:
                logo_val = invoice_config.logo.path
            except Exception:
                logo_val = invoice_config.logo.url

        restaurant_dict = {
            "name": (invoice_config.restaurant_name or "Nextora POS") if invoice_config.restaurant_name else " ",
            "subtitle": invoice_config.custom_header_text or "",
            "address": invoice_config.address or "",
            "phone": invoice_config.phone or "",
            "gst": invoice_config.gstin if (show_gst_breakdown or invoice_config.show_gstin) else "",
            "logo": logo_val,
        }

        invoice_dict = {
            "number": "TEST-0001" if show_invoice_num else "",
            "date": "Test Print",
            "time": "",
        }

        footer_dict = {
            "thank_you": invoice_config.thank_you_message or "Thank you for your visit!",
            "visit_again": "Visit Again" if invoice_config.thank_you_message else "",
            "return_policy": invoice_config.terms_notes or "",
            "website": invoice_config.website or "",
            "custom_text": invoice_config.custom_footer_text or "",
        }

        test_data = {
            "restaurant": restaurant_dict,
            "invoice": invoice_dict,
            "order_id": "TEST-ORD" if invoice_config.show_order_number else "",
            "cashier": "Test Cashier" if invoice_config.show_cashier_name else "",
            "customer": "Test Customer" if invoice_config.show_customer_name else "",
            "table": "T1" if invoice_config.show_table_number else "",
            "order_type": "DINE-IN" if invoice_config.show_order_type else "",
            "items": [
                {"name": "Test Item 1", "qty": 1, "price": "100.00", "amount": "100.00"},
                {"name": "Test Item 2", "qty": 2, "price": "50.00", "amount": "100.00"},
            ],
            "subtotal": "200.00",
            "discount": "0.00" if show_discount else "0.00",
            "gst": "10.00" if show_gst_breakdown else "0.00",
            "tax": "10.00" if show_gst_breakdown else "0.00",
            "grand_total": "210.00",
            "total": "210.00",
            "payment_method": "CASH" if show_payment_method else "",
            "footer": footer_dict,
            "paper_width_mm": 80 if "80" in str(invoice_config.paper_size or "80mm") else 58,
            "template": "restaurant",
            "receipt_type": "TEST RECEIPT",
            "diagnostic": True,
        }

        client = PrintServiceClient()
        result = client.print_receipt(
            printer_name=printer_name,
            receipt_data=test_data,
            copies=1,
        )

        if result.success:
            return JsonResponse({
                "success": True,
                "message": f"Test receipt sent to '{printer_name}'.",
                "job_id": result.data.get("job_id", ""),
            })
        else:
            return JsonResponse({
                "success": False,
                "error": result.error or "Print Service returned an error.",
            }, status=500)


class InvoiceConfigurationPreviewView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """HTMX endpoint returning the live receipt preview HTML.

    Reads the POST data as JSON (the current Alpine.js config state)
    and renders the preview partial. This enables real-time preview updates
    as the user toggles settings.
    """
    permission_required = "orders.view"
    template_name = "ordering/partials/invoice_config_preview.html"

    def post(self, request, *args, **kwargs):
        try:
            config_data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            config_data = {}

        # Build a config-like object from the POST data for preview rendering
        config = self._build_config_from_dict(config_data)
        preview_data = _build_demo_preview_data(config)

        return render(request, self.template_name, {
            "preview_data": preview_data,
            "config": config,
        })

    def _build_config_from_dict(self, data):
        """Build a simple object from config dict for preview rendering."""
        class ConfigProxy:
            pass

        cfg = ConfigProxy()
        try:
            fields = InvoiceConfiguration._meta.get_fields()
        except Exception:
            fields = []
        for field in fields:
            name = field.name
            if name in data:
                setattr(cfg, name, data[name])
            else:
                try:
                    setattr(cfg, name, getattr(field, "default", ""))
                except Exception:
                    setattr(cfg, name, "")
        return cfg


class InvoiceReprintView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    """Reprint an invoice with DUPLICATE marking.

    POST /ordering/invoice/<uuid:invoice_id>/reprint/
    Sends a reprint to the Print Service with is_reprint=True.
    """
    permission_required = "orders.update"

    def post(self, request, invoice_id, *args, **kwargs):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        order = invoice.order

        if order.status != OrderStatus.SETTLED:
            return JsonResponse({"success": False, "error": "Order is not settled."}, status=400)

        import uuid as _uuid
        idempotency_key = f"reprint-{str(_uuid.uuid4().hex)}"

        print_result = dispatch_to_print_service(
            order=order,
            invoice=invoice,
            idempotency_key=idempotency_key,
        )

        if print_result.get("success"):
            try:
                from contexts.audit.services import record_audit
                record_audit(
                    "invoice.reprinted",
                    entity_type="invoice",
                    entity_id=invoice.id,
                    changes={
                        "invoice_number": invoice.number,
                        "order_number": order.order_number,
                        "reprinted_by": str(request.user.id) if request.user.is_authenticated else None,
                    },
                )
            except Exception:
                pass

        return JsonResponse(print_result)


class InvoiceSnapshotDetailView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    """View a historical invoice using its immutable snapshot.

    GET /ordering/invoice/<uuid:invoice_id>/snapshot/
    Renders the thermal receipt template using the InvoiceSnapshot data.
    """
    permission_required = "orders.view"
    template_name = "pages/invoice/thermal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_id = self.kwargs.get("invoice_id")
        invoice = get_object_or_404(Invoice, id=invoice_id)

        snapshot = InvoiceSnapshot.objects.filter(invoice=invoice).first()

        if snapshot:
            context["snapshot"] = snapshot
            context["using_snapshot"] = True
            context["paper_width"] = snapshot.paper_size or "80mm"
            context["currency_symbol"] = snapshot.currency_symbol or "₹"
        else:
            context["snapshot"] = None
            context["using_snapshot"] = False
            context["paper_width"] = "80mm"
            context["currency_symbol"] = "₹"

        context["invoice"] = invoice
        context["order"] = invoice.order
        context["is_reprint"] = self.request.GET.get("copy", "") == "duplicate"

        return context
