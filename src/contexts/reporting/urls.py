from django.urls import path
from .views import (
    DashboardHomeView,
    SalesReportView,
    ItemReportView,
    InventoryReportView,
    TaxReportView,
    InvoiceDetailView,
    EmailInvoiceView,
    EmailShareModalView,
)

app_name = "reporting"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("<uuid:tenant_id>/", DashboardHomeView.as_view(), name="home_tenant"),
    path("sales/", SalesReportView.as_view(), name="sales"),
    path("<uuid:tenant_id>/sales/", SalesReportView.as_view(), name="sales_tenant"),
    path("items/", ItemReportView.as_view(), name="items"),
    path("<uuid:tenant_id>/items/", ItemReportView.as_view(), name="items_tenant"),
    path("inventory/", InventoryReportView.as_view(), name="inventory"),
    path("<uuid:tenant_id>/inventory/", InventoryReportView.as_view(), name="inventory_tenant"),
    path("tax/", TaxReportView.as_view(), name="tax"),
    path("<uuid:tenant_id>/tax/", TaxReportView.as_view(), name="tax_tenant"),
    path("invoice/<uuid:order_id>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("<uuid:tenant_id>/invoice/<uuid:order_id>/", InvoiceDetailView.as_view(), name="invoice_detail_tenant"),
    path("invoice/<uuid:order_id>/email/modal/", EmailShareModalView.as_view(), name="email_modal"),
    path("invoice/<uuid:order_id>/email/", EmailInvoiceView.as_view(), name="email_invoice"),
    path("<uuid:tenant_id>/invoice/<uuid:order_id>/email/", EmailInvoiceView.as_view(), name="email_invoice_tenant"),
]
