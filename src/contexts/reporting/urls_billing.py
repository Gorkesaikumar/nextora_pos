from django.urls import path
from django.views.generic import TemplateView

from .views import (
    BillingDashboardView,
    InvoiceListView,
    PaymentHistoryView,
    SalesReportView,
    TaxReportView,
    WhatsAppShareModalView,
    WhatsAppSendActionView,
    TaxSummaryView,
    BillingAuditLogView,
    InvoiceHistoryModalView,
)

app_name = "billing"

urlpatterns = [
    path("dashboard/", BillingDashboardView.as_view(), name="dashboard"),
    path("invoices/", InvoiceListView.as_view(), name="invoices"),
    path("payments/", PaymentHistoryView.as_view(), name="payments"),
    path("reports/", SalesReportView.as_view(), name="reports"),
    path("gst-reports/", TaxReportView.as_view(), name="gst_reports"),
    path("whatsapp/<uuid:order_id>/modal/", WhatsAppShareModalView.as_view(), name="whatsapp_modal"),
    path("whatsapp/<uuid:order_id>/send/", WhatsAppSendActionView.as_view(), name="whatsapp_send"),
    path("audit/", BillingAuditLogView.as_view(), name="audit_log"),
    path("invoices/<uuid:order_id>/history/", InvoiceHistoryModalView.as_view(), name="invoice_history_modal"),

    
    # Placeholders for unimplemented features
    path("gst-filing/", TemplateView.as_view(template_name="reporting/coming_soon.html"), name="gst_filing"),
    path("tax-summary/", TaxSummaryView.as_view(), name="tax_summary"),
    path("refunds/", TemplateView.as_view(template_name="reporting/coming_soon.html"), name="refunds"),
    path("whatsapp/", TemplateView.as_view(template_name="reporting/coming_soon.html"), name="whatsapp"),
    path("settings/", TemplateView.as_view(template_name="reporting/coming_soon.html"), name="settings"),
]
