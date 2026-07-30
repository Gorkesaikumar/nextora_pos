import io
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import datetime

class PDFExportService:
    @staticmethod
    def generate(title: str, headers: list[str], rows: list[list], date_range: str = "", generated_by: str = "System"):
        # We will reuse the existing 'reporting/export_pdf.html' template
        # or supply a standard context if we want to improve it.
        context = {
            'title': title.replace('_', ' ').title(),
            'header': headers,
            'rows': rows,
            'date_range': date_range,
            'generated_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'generated_by': generated_by,
        }
        
        html_string = render_to_string('reporting/export_pdf.html', context)
        
        output = io.BytesIO()
        # Using xhtml2pdf to render
        pisa_status = pisa.CreatePDF(html_string, dest=output)
        
        if pisa_status.err:
            return HttpResponse('PDF Generation Error', status=500)
            
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title}.pdf"'
        return response
