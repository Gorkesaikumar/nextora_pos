"""URL Routing for reporting and dashboard APIs."""
from django.urls import path

from .views import (
    DashboardSummaryView,
    SalesMetricsView,
    TopSellingItemsView,
    TopCategoriesView,
    PaymentSummaryView,
    GSTReportsView,
    SalesChartsView,
    ProfitReportsView,
    ExportAPIView,
    KDSMetricsView,
)

app_name = "reporting_api"

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("sales/", SalesMetricsView.as_view(), name="sales-metrics"),
    path("top-items/", TopSellingItemsView.as_view(), name="top-items"),
    path("top-categories/", TopCategoriesView.as_view(), name="top-categories"),
    path("payments/", PaymentSummaryView.as_view(), name="payment-summary"),
    path("gst/", GSTReportsView.as_view(), name="gst-reports"),
    path("charts/", SalesChartsView.as_view(), name="sales-charts"),
    path("profit/", ProfitReportsView.as_view(), name="profit-reports"),
    path("export/", ExportAPIView.as_view(), name="report-export"),
    path("kds-metrics/", KDSMetricsView.as_view(), name="kds-metrics"),
]
