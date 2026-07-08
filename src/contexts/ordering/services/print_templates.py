"""Template engine for ESC/POS receipt generation."""
from decimal import Decimal
from abc import ABC, abstractmethod
from typing import Any

from contexts.ordering.models import Order, Invoice, KOT

# --- ESC/POS Constants ---
_ESC_INIT = b"\x1b\x40"
_ESC_ALIGN_LEFT = b"\x1b\x61\x00"
_ESC_ALIGN_CENTER = b"\x1b\x61\x01"
_ESC_BOLD_ON = b"\x1b\x45\x01"
_ESC_BOLD_OFF = b"\x1b\x45\x00"
_GS_DOUBLE = b"\x1d\x21\x11"
_GS_NORMAL = b"\x1d\x21\x00"
_CUT = b"\x1d\x56\x00"
_FEED = b"\n\n\n"
_KICK_DRAWER = b"\x1b\x70\x00\x19\xfa" # Kick cash drawer 1


def _line(left: str, right: str, width: int) -> str:
    space = width - len(left) - len(right)
    return left + (" " * max(1, space)) + right


def _rule(width: int, char: str = "-") -> str:
    return char * width


def _resolve_branch_metadata(order: Order) -> tuple[str, str, str]:
    business = getattr(order.tenant, "name", "NEXTORA POS").upper()
    address = "123 Gourmet Avenue, Suite 400\nMG Road, Bangalore - 560001"
    gstin_vat = "GSTIN: 29ABCDE1234F1Z5"

    try:
        from contexts.restaurant.models import Branch
        branch = Branch.objects.filter(id=order.location_id).first()
        if branch:
            if getattr(branch, "name", None):
                business = f"{business} - {branch.name}".upper()
            if getattr(branch, "address", None):
                address = branch.address
            if getattr(branch, "gstin", None):
                gstin_vat = f"GSTIN: {branch.gstin}"
            elif getattr(branch, "vat_number", None):
                gstin_vat = f"VAT: {branch.vat_number}"
    except Exception:
        pass

    return business, address, gstin_vat


def _resolve_table_info(order: Order) -> str:
    if not order.table_id:
        return ""
    try:
        from contexts.restaurant.models.layout import DiningTable
        table = DiningTable.objects.filter(id=order.table_id).first()
        if table:
            return f"Table {table.number}" if getattr(table, "number", None) else table.name
    except Exception:
        pass
    return "Table Dine-In"


class BasePrintTemplate(ABC):
    """Abstract base template for generating receipts and KOTs."""
    
    def __init__(self, paper_width: str = "80mm"):
        self.paper_width = paper_width
        self.width_cols = 32 if paper_width == "58mm" else 48
    
    @abstractmethod
    def render_text(self, context: Any) -> str:
        """Render human-readable text block."""
        pass
        
    @abstractmethod
    def render_escpos(self, context: Any) -> bytes:
        """Render raw ESC/POS bytes."""
        pass


class CustomerReceiptTemplate(BasePrintTemplate):
    """Template for Customer Tax Invoice Receipt."""

    def render_text(self, invoice: Invoice, copy_type: str = "") -> str:
        order = invoice.order
        width = self.width_cols
        biz_name, addr, tax_id = _resolve_branch_metadata(order)
        addr_lines = addr.split("\n")

        rows = []
        rows.append(f"[ LOGO: {biz_name} ]".center(width))
        rows.append(biz_name.center(width))
        for line in addr_lines:
            rows.append(line.strip().center(width))
        rows.append(tax_id.center(width))
        rows.append("TAX INVOICE".center(width))
        
        if copy_type:
            rows.append(f"*** {copy_type} ***".center(width))
        else:
            rows.append("*** CUSTOMER COPY ***".center(width))
            
        rows.append(_rule(width, "="))
        rows.append(_line("Invoice #", invoice.number, width))
        rows.append(_line("Date & Time", invoice.issued_at.strftime("%d-%m-%Y %H:%M:%S"), width))
        
        from contexts.ordering.services.printing import _resolve_cashier_name
        rows.append(_line("Cashier", _resolve_cashier_name(order)[:width - 10], width))

        if order.customer_name:
            rows.append(_line("Customer", order.customer_name[:width - 10], width))

        table_info = _resolve_table_info(order)
        if table_info:
            rows.append(_line("Table", table_info, width))

        rows.append(_line("Order Type", order.get_type_display(), width))
        rows.append(_rule(width))
        
        if width <= 34:
            rows.append("QTY ITEM")
            rows.append(_line("    UNIT PRICE", "TOTAL", width))
        else:
            rows.append(_line("QTY ITEM", "UNIT PRICE     TOTAL", width))
        rows.append(_rule(width))

        for item in order.items.filter(status="active"):
            qty_str = str(int(item.qty)) if item.qty == int(item.qty) else str(item.qty)
            line_tot = f"{item.line_total:.2f}"
            unit_pr = f"{item.unit_price:.2f}"

            if width <= 34:
                rows.append(f"{qty_str} x {item.name_snapshot}"[:width])
                rows.append(_line(f"    @ {unit_pr}", line_tot, width))
            else:
                item_left = f"{qty_str} x {item.name_snapshot[:width - 22]}"
                rows.append(_line(f"{item_left} @ {unit_pr}", line_tot, width))

            if getattr(item, "modifiers_total", Decimal("0.00")) > 0:
                rows.append(f"    + Modifiers: {item.modifiers_total:.2f}"[:width])

        rows.append(_rule(width))
        rows.append(_line("Subtotal", f"{order.subtotal:.2f}", width))

        if order.discount_amount and order.discount_amount > 0:
            rows.append(_line("Discount", f"-{order.discount_amount:.2f}", width))
        if order.service_charge_amount and order.service_charge_amount > 0:
            rows.append(_line("Service Charge", f"{order.service_charge_amount:.2f}", width))
        if order.cgst and order.cgst > 0:
            rows.append(_line("CGST", f"{order.cgst:.2f}", width))
            rows.append(_line("SGST", f"{order.sgst:.2f}", width))
        if order.igst and order.igst > 0:
            rows.append(_line("IGST", f"{order.igst:.2f}", width))
        if order.cess and order.cess > 0:
            rows.append(_line("Cess", f"{order.cess:.2f}", width))
        if order.round_off and order.round_off != 0:
            rows.append(_line("Round Off", f"{order.round_off:.2f}", width))

        rows.append(_rule(width, "="))
        rows.append(_line("GRAND TOTAL", f"{order.total:.2f}", width))
        rows.append(_rule(width, "="))

        payments = list(order.payments.filter(kind="payment"))
        if payments:
            methods = ", ".join(p.method.upper() for p in payments)
            amount_paid = sum((p.tendered or p.amount) for p in payments)
        else:
            methods = "CASH"
            amount_paid = order.total

        balance_returned = max(Decimal("0.00"), Decimal(str(amount_paid)) - order.total)

        rows.append(_line("Payment Method", methods, width))
        rows.append(_line("Amount Paid", f"{Decimal(str(amount_paid)):.2f}", width))
        rows.append(_line("Balance Returned", f"{balance_returned:.2f}", width))
        rows.append(_rule(width))
        rows.append("")
        
        if copy_type == "RESTAURANT COPY":
            rows.append("ACCOUNTING & AUDIT RECORD".center(width))
            rows.append(_rule(width))
            rows.append(_line("Internal Order #", str(order.id)[:18], width))
            
            payment_ref = payments[0].reference if payments and payments[0].reference else "N/A"
            rows.append(_line("Internal Txn ID", payment_ref[:18], width))
            
            rows.append(_line("Branch Name", biz_name[:18], width))
            rows.append(_line("Terminal ID", "POS-TRM-01", width))
            rows.append(_line("Cashier ID", str(order.created_by)[:18] if order.created_by else "POS", width))
            rows.append(_line("Shift Number", "SHIFT-01", width))
            rows.append(_line("Company Name", getattr(order.tenant, "name", "NEXTORA")[:18], width))
            rows.append(_line("Company ID", str(order.tenant_id)[:18], width))
            
            audit_ref = f"AUD-{order.id.hex[:12].upper()}"
            rows.append(_line("Audit Ref", audit_ref, width))
            rows.append(_line("Print Timestamp", invoice.issued_at.strftime("%Y-%m-%d %H:%M:%S"), width))
            
            rows.append(_rule(width))
            rows.append("ACCOUNTING & AUDIT ARCHIVE RECORD".center(width))
            rows.append("RETAIN FOR FINANCIAL COMPLIANCE".center(width))
        else:
            rows.append("THANK YOU FOR YOUR VISIT!".center(width))
            rows.append("PLEASE COME AGAIN".center(width))
            
        rows.append("")
        return "\n".join(rows) + "\n"

    def render_escpos(self, invoice: Invoice, copy_type: str = "") -> bytes:
        text = self.render_text(invoice, copy_type)
        lines = text.split("\n")
        buf = bytearray(_ESC_INIT)

        for line in lines:
            if "[ LOGO:" in line or "TAX INVOICE" in line or "***" in line:
                buf.extend(_ESC_ALIGN_CENTER)
                buf.extend(_ESC_BOLD_ON)
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(_ESC_BOLD_OFF)
                buf.extend(_ESC_ALIGN_LEFT)
                buf.extend(b"\n")
            elif "GRAND TOTAL" in line:
                buf.extend(_ESC_BOLD_ON)
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(_ESC_BOLD_OFF)
                buf.extend(b"\n")
            else:
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(b"\n")

        buf.extend(_FEED)
        buf.extend(_CUT)
        
        # Fire cash drawer ONLY for customer copy
        if copy_type == "":
            buf.extend(_KICK_DRAWER)
            
        return bytes(buf)


class KOTTemplate(BasePrintTemplate):
    """Template for Kitchen Order Ticket."""

    def render_text(self, kot: KOT) -> str:
        width = self.width_cols
        biz_name, _, _ = _resolve_branch_metadata(kot.order)

        rows = []
        rows.append(_rule(width, "="))
        rows.append("KITCHEN ORDER TICKET".center(width))
        rows.append(biz_name.center(width))
        rows.append(_rule(width, "="))

        rows.append(_line("KOT Number:", f"#{kot.number}", width))
        order_num = str(kot.order.order_number or kot.order.id)
        rows.append(_line("Order Number:", order_num[:width - 15], width))
        rows.append(_line("Date & Time:", kot.created_at_kot.strftime("%d-%m-%Y %H:%M:%S"), width))
        rows.append(_line("Order Type:", kot.order.get_type_display(), width))

        table_info = _resolve_table_info(kot.order)
        if table_info:
            rows.append(_line("Table:", table_info, width))

        if kot.order.customer_name:
            rows.append(_line("Customer:", kot.order.customer_name[:width - 11], width))

        rows.append(_rule(width, "="))
        rows.append("QTY   ITEM DETAILS & MODIFIERS".ljust(width)[:width])
        rows.append(_rule(width, "="))

        items = kot.items.all()
        if not items.exists():
            rows.append("No items routed to this KOT".center(width))
        else:
            for item in items:
                qty_str = str(int(item.qty)) if item.qty == int(item.qty) else str(item.qty)
                item_header = f"[ {qty_str} ]  {item.name_snapshot.upper()}"
                rows.append(item_header[:width])

                try:
                    order_item = getattr(item, "order_item", None)
                    if order_item:
                        for mod in order_item.modifiers.all():
                            mod_qty = f" ({int(mod.qty)}x)" if mod.qty > 1 else ""
                            rows.append(f"       + {mod.name_snapshot}{mod_qty}"[:width])
                except Exception:
                    pass

                if item.notes:
                    rows.append(f"       *** NOTE: {item.notes} ***"[:width])
                elif getattr(item, "order_item", None) and getattr(item.order_item, "notes", None):
                    rows.append(f"       *** NOTE: {item.order_item.notes} ***"[:width])

                rows.append(_rule(width, "-"))

        rows.append(_rule(width, "="))
        rows.append("*** END OF KOT ***".center(width))
        rows.append("")
        return "\n".join(rows) + "\n"

    def render_escpos(self, kot: KOT) -> bytes:
        text = self.render_text(kot)
        lines = text.split("\n")
        buf = bytearray(_ESC_INIT)

        for line in lines:
            stripped = line.strip()
            if "KITCHEN ORDER TICKET" in line:
                buf.extend(_ESC_ALIGN_CENTER)
                buf.extend(_GS_DOUBLE)
                buf.extend(_ESC_BOLD_ON)
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(_ESC_BOLD_OFF)
                buf.extend(_GS_NORMAL)
                buf.extend(_ESC_ALIGN_LEFT)
                buf.extend(b"\n")
            elif stripped.startswith("[ ") and " ]" in stripped:
                buf.extend(_ESC_BOLD_ON)
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(_ESC_BOLD_OFF)
                buf.extend(b"\n")
            elif stripped.startswith("*** NOTE:") or stripped.startswith("KOT Number:"):
                buf.extend(_ESC_BOLD_ON)
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(_ESC_BOLD_OFF)
                buf.extend(b"\n")
            else:
                buf.extend(line.encode("ascii", errors="replace"))
                buf.extend(b"\n")

        buf.extend(_FEED)
        buf.extend(_CUT)
        return bytes(buf)
