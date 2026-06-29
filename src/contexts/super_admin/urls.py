from django.urls import path

from . import views

app_name = "super_admin"

urlpatterns = [
    path("login/", views.PlatformLoginView.as_view(), name="login"),
    path("logout/", views.PlatformLogoutView.as_view(), name="logout"),
    path("", views.PlatformDashboardView.as_view(), name="dashboard"),
    path("tenants/", views.PlatformTenantListView.as_view(), name="tenant_list"),
    path("users/", views.PlatformUserListView.as_view(), name="user_list"),
    path("subscriptions/", views.PlatformSubscriptionListView.as_view(), name="subscription_list"),
    path("invoices/", views.PlatformInvoiceListView.as_view(), name="invoice_list"),
    path("payments/", views.PlatformPaymentListView.as_view(), name="payment_list"),
    path("coupons/", views.PlatformCouponListView.as_view(), name="coupon_list"),
    path("features/", views.PlatformFeatureFlagListView.as_view(), name="feature_flag_list"),
    path("analytics/", views.PlatformAnalyticsView.as_view(), name="analytics"),
    path("reports/", views.PlatformReportListView.as_view(), name="report_list"),
    path("audit/", views.PlatformAuditLogListView.as_view(), name="audit_log_list"),
    path("notifications/", views.PlatformNotificationListView.as_view(), name="notification_list"),
    path("monitoring/", views.PlatformMonitoringView.as_view(), name="monitoring"),
    path("settings/", views.PlatformSettingsView.as_view(), name="settings"),
]
