from django.urls import path
from django.views.generic import TemplateView

from .views import (
    BillingDashboardView,
    InvoiceListView,
    InvoiceDetailView,
    InvoiceDownloadPDFView,
    PaymentHistoryView,
    SalesReportView,
    TaxReportView,
    WhatsAppShareModalView,
    WhatsAppSendActionView,
    TaxSummaryView,
    BillingAuditLogView,
    InvoiceHistoryModalView,
    EmailShareModalView,
    EmailInvoiceView,
    GSTFilingView,
    RefundBillsView,
    RefundLookupView,
    InitiateRefundView,
    WhatsAppHistoryView,
    BillingSettingsView,
)

from contexts.billing.upgrade_views import SubscriptionUpgradeView, ValidateCouponAPIView

app_name = "billing"

urlpatterns = [
    path("upgrade/", SubscriptionUpgradeView.as_view(), name="upgrade"),
    path("upgrade/validate-coupon/", ValidateCouponAPIView.as_view(), name="validate_coupon"),
    path("dashboard/", BillingDashboardView.as_view(), name="dashboard"),
    path("<uuid:tenant_id>/dashboard/", BillingDashboardView.as_view(), name="dashboard_tenant"),
    
    path("invoices/", InvoiceListView.as_view(), name="invoices"),
    path("<uuid:tenant_id>/invoices/", InvoiceListView.as_view(), name="invoices_tenant"),

    path("invoices/<uuid:order_id>/view/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("<uuid:tenant_id>/invoices/<uuid:order_id>/view/", InvoiceDetailView.as_view(), name="invoice_detail_tenant"),

    path("invoices/<uuid:order_id>/pdf/", InvoiceDownloadPDFView.as_view(), name="invoice_pdf"),
    path("<uuid:tenant_id>/invoices/<uuid:order_id>/pdf/", InvoiceDownloadPDFView.as_view(), name="invoice_pdf_tenant"),

    path("invoices/<uuid:order_id>/history/", InvoiceHistoryModalView.as_view(), name="invoice_history_modal"),
    path("<uuid:tenant_id>/invoices/<uuid:order_id>/history/", InvoiceHistoryModalView.as_view(), name="invoice_history_modal_tenant"),

    path("invoices/<uuid:order_id>/email/modal/", EmailShareModalView.as_view(), name="email_modal"),
    path("<uuid:tenant_id>/invoices/<uuid:order_id>/email/modal/", EmailShareModalView.as_view(), name="email_modal_tenant"),

    path("invoices/<uuid:order_id>/email/", EmailInvoiceView.as_view(), name="email_invoice"),
    path("<uuid:tenant_id>/invoices/<uuid:order_id>/email/", EmailInvoiceView.as_view(), name="email_invoice_tenant"),

    path("whatsapp/<uuid:order_id>/modal/", WhatsAppShareModalView.as_view(), name="whatsapp_modal"),
    path("<uuid:tenant_id>/whatsapp/<uuid:order_id>/modal/", WhatsAppShareModalView.as_view(), name="whatsapp_modal_tenant"),

    path("whatsapp/<uuid:order_id>/send/", WhatsAppSendActionView.as_view(), name="whatsapp_send"),
    path("<uuid:tenant_id>/whatsapp/<uuid:order_id>/send/", WhatsAppSendActionView.as_view(), name="whatsapp_send_tenant"),

    path("payments/", PaymentHistoryView.as_view(), name="payments"),
    path("<uuid:tenant_id>/payments/", PaymentHistoryView.as_view(), name="payments_tenant"),

    path("reports/", SalesReportView.as_view(), name="reports"),
    path("<uuid:tenant_id>/reports/", SalesReportView.as_view(), name="reports_tenant"),

    path("gst-reports/", TaxReportView.as_view(), name="gst_reports"),
    path("<uuid:tenant_id>/gst-reports/", TaxReportView.as_view(), name="gst_reports_tenant"),

    path("audit/", BillingAuditLogView.as_view(), name="audit_log"),
    path("<uuid:tenant_id>/audit/", BillingAuditLogView.as_view(), name="audit_log_tenant"),

    # Final Phase Additions
    path("gst-filing/", GSTFilingView.as_view(), name="gst_filing"),
    path("<uuid:tenant_id>/gst-filing/", GSTFilingView.as_view(), name="gst_filing_tenant"),
    
    path("tax-summary/", TaxSummaryView.as_view(), name="tax_summary"),
    path("<uuid:tenant_id>/tax-summary/", TaxSummaryView.as_view(), name="tax_summary_tenant"),
    
    path("refunds/", RefundBillsView.as_view(), name="refunds"),
    path("<uuid:tenant_id>/refunds/", RefundBillsView.as_view(), name="refunds_tenant"),
    
    path("refunds/lookup/", RefundLookupView.as_view(), name="refunds_lookup"),
    path("<uuid:tenant_id>/refunds/lookup/", RefundLookupView.as_view(), name="refunds_lookup_tenant"),

    path("refunds/initiate/", InitiateRefundView.as_view(), name="refunds_initiate"),
    path("<uuid:tenant_id>/refunds/initiate/", InitiateRefundView.as_view(), name="refunds_initiate_tenant"),

    path("whatsapp/", WhatsAppHistoryView.as_view(), name="whatsapp"),
    path("<uuid:tenant_id>/whatsapp/", WhatsAppHistoryView.as_view(), name="whatsapp_tenant"),
    
    path("settings/", BillingSettingsView.as_view(), name="settings"),
    path("<uuid:tenant_id>/settings/", BillingSettingsView.as_view(), name="settings_tenant"),
]
