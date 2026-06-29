from django.urls import path
from .views import (
    DashboardHomeView,
    SalesReportView,
    ItemReportView,
    InventoryReportView,
    TaxReportView,
    InvoiceDetailView,
    EmailInvoiceView,
)

app_name = "reporting"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("items/", ItemReportView.as_view(), name="items"),
    path("inventory/", InventoryReportView.as_view(), name="inventory"),
    path("tax/", TaxReportView.as_view(), name="tax"),
    path("invoice/<uuid:order_id>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoice/<uuid:order_id>/email/", EmailInvoiceView.as_view(), name="email_invoice"),
]
