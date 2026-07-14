from django.urls import path

from . import views
from . import subscription_views as sub_views

app_name = "super_admin"

urlpatterns = [
    path("login/", views.PlatformLoginView.as_view(), name="login"),
    path("logout/", views.PlatformLogoutView.as_view(), name="logout"),
    path("", views.PlatformDashboardView.as_view(), name="dashboard"),
    path("tenants/", views.PlatformTenantListView.as_view(), name="tenant_list"),
    path("users/", views.PlatformUserListView.as_view(), name="user_list"),
    path("subscriptions/", views.PlatformSubscriptionListView.as_view(), name="subscription_list"),
    
    # Complete SaaS Subscription Management Routes
    path("plans/", sub_views.PlatformPlanListView.as_view(), name="plan_list"),
    path("plans/create/", sub_views.PlatformPlanCreateEditView.as_view(), name="plan_create"),
    path("plans/<uuid:plan_id>/edit/", sub_views.PlatformPlanCreateEditView.as_view(), name="plan_edit"),
    path("plans/<uuid:plan_id>/delete/", sub_views.PlatformPlanDeleteView.as_view(), name="plan_delete"),
    path("trials/", sub_views.PlatformTrialConfigView.as_view(), name="trial_config"),
    path("visibility/", sub_views.PlatformVisibilityConfigView.as_view(), name="visibility_config"),
    path("saas-coupons/", sub_views.PlatformCouponDiscountListView.as_view(), name="coupon_discount_list"),
    path("saas-coupons/create/", sub_views.PlatformCouponCreateEditView.as_view(), name="coupon_create"),
    path("saas-coupons/<uuid:coupon_id>/edit/", sub_views.PlatformCouponCreateEditView.as_view(), name="coupon_edit"),
    path("saas-coupons/<uuid:coupon_id>/delete/", sub_views.PlatformCouponDeleteView.as_view(), name="coupon_delete"),
    path("saas-coupons/<uuid:coupon_id>/toggle/", sub_views.PlatformCouponToggleStatusView.as_view(), name="coupon_toggle"),
    path("saas-coupons/tenant-discounts/create/", sub_views.PlatformTenantDiscountCreateView.as_view(), name="tenant_discount_create"),
    path("saas-coupons/tenant-discounts/<uuid:discount_id>/edit/", sub_views.PlatformTenantDiscountCreateView.as_view(), name="tenant_discount_edit"),

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

