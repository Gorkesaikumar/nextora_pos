"""Thermal receipt rendering (KOT + tax invoice).

Produces a plain-text layout sized for thermal rolls, plus an ESC/POS byte
builder (init + text + paper cut) ready to send to a network/USB printer.
Default width 32 chars (58mm); pass width=48 for 80mm.
"""
from contexts.ordering.models import KOT, Invoice


def _line(left: str, right: str, width: int) -> str:
    space = width - len(left) - len(right)
    return left + (" " * max(1, space)) + right


def _rule(width: int, char: str = "-") -> str:
    return char * width


def render_kot_text(kot: KOT, *, width: int = 32) -> str:
    rows = [
        "KITCHEN ORDER TICKET".center(width),
        _line(f"KOT #{kot.number}", kot.created_at_kot.strftime("%H:%M"), width),
        _line("Order", str(kot.order.order_number), width),
        _rule(width),
    ]
    for item in kot.items.all():
        rows.append(_line(f"{int(item.qty)} x {item.name_snapshot}"[:width - 1], "", width))
        if item.notes:
            rows.append(f"   * {item.notes}"[:width])
    rows.append(_rule(width))
    return "\n".join(rows) + "\n"


def render_invoice_text(invoice: Invoice, *, width: int = 32, business: str = "Nextora POS") -> str:
    order = invoice.order
    rows = [
        business.center(width),
        "TAX INVOICE".center(width),
        _line("Invoice", invoice.number, width),
        _line("Date", invoice.issued_at.strftime("%d-%m-%Y %H:%M"), width),
        _rule(width),
    ]
    for item in order.items.filter(status="active"):
        rows.append(item.name_snapshot[:width])
        rows.append(_line(f"  {int(item.qty)} x {item.unit_price}",
                          f"{item.line_total}", width))
    rows.append(_rule(width))
    rows.append(_line("Subtotal", f"{order.subtotal}", width))
    if order.discount_amount:
        rows.append(_line("Discount", f"-{order.discount_amount}", width))
    if order.service_charge_amount:
        rows.append(_line("Service Chg", f"{order.service_charge_amount}", width))
    if order.cgst or order.sgst:
        rows.append(_line("CGST", f"{order.cgst}", width))
        rows.append(_line("SGST", f"{order.sgst}", width))
    if order.igst:
        rows.append(_line("IGST", f"{order.igst}", width))
    if order.cess:
        rows.append(_line("Cess", f"{order.cess}", width))
    if order.round_off:
        rows.append(_line("Round Off", f"{order.round_off}", width))
    rows.append(_rule(width, "="))
    rows.append(_line("TOTAL", f"{order.total}", width))
    rows.append(_rule(width, "="))
    for payment in order.payments.filter(kind="payment"):
        rows.append(_line(payment.method.upper(), f"{payment.amount}", width))
    rows.append("")
    rows.append("Thank you! Visit again".center(width))
    return "\n".join(rows) + "\n"


# --- ESC/POS ---------------------------------------------------------------
_ESC_INIT = b"\x1b\x40"          # initialise printer
_CUT = b"\x1d\x56\x00"           # full cut
_FEED = b"\n\n\n"


def to_escpos(text: str) -> bytes:
    return _ESC_INIT + text.encode("ascii", errors="replace") + _FEED + _CUT
