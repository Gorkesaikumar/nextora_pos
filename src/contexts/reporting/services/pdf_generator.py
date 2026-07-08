from io import BytesIO
import logging

from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from contexts.ordering.models import Order
from contexts.tenants.models import Branch

logger = logging.getLogger(__name__)

def generate_invoice_pdf(order_id: str) -> tuple[str, bytes]:
    """
    Generates a PDF invoice for the given order_id.
    Returns a tuple of (filename, pdf_bytes).
    """
    try:
        order = get_object_or_404(Order.objects.select_related('invoice').prefetch_related('items'), id=order_id)
        
        branch = None
        if order.location_id:
            try:
                branch = Branch.objects.get(id=order.location_id)
            except Branch.DoesNotExist:
                pass
                
        # Prepare context for the PDF template
        context = {
            'order': order,
            'branch': branch,
            'subtotal': order.subtotal,
            'tax': order.tax_amount,
            'discount': order.discount_amount,
            'total': order.total,
        }
        
        # Render HTML
        html_string = render_to_string('reporting/invoice_pdf.html', context)
        
        # Generate PDF bytes
        font_config = FontConfiguration()
        html = HTML(string=html_string)
        
        # We can also add default CSS if needed
        # css = CSS(string='@page { size: A4; margin: 1cm; }', font_config=font_config)
        
        pdf_file = html.write_pdf(font_config=font_config)
        
        invoice_number = order.invoice.number if hasattr(order, 'invoice') else order.order_number
        filename = f"Invoice_{invoice_number}.pdf"
        
        return filename, pdf_file
        
    except Exception as e:
        logger.error(f"Failed to generate invoice PDF for order {order_id}: {str(e)}")
        raise
