import csv
import io
from django.http import HttpResponse

class CSVExportService:
    @staticmethod
    def generate(title: str, headers: list[str], rows: list[list]):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{title}.csv"'
        
        # Write UTF-8 BOM so Excel opens it correctly with special chars
        response.write('\ufeff'.encode('utf8'))
        
        writer = csv.writer(response, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
            
        return response
