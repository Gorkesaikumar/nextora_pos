"""Root URL configuration.

Surface is split into three concerns:
  * /            — web (Django Templates) delivery — added per context.
  * /api/v1/     — versioned, API-first REST surface.
  * /healthz...  — unauthenticated operational probes (outside versioning).
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from shared.api.health import liveness, readiness

from django.views.generic import TemplateView

urlpatterns = [
    # --- Operational probes (no auth, no tenant) --------------------------
    path("healthz/live/", liveness, name="health-live"),
    path("healthz/ready/", readiness, name="health-ready"),
    # --- Gateway webhooks (unauthenticated, tenant-agnostic) --------------
    path("", include("contexts.billing.api.urls")),
    # --- Admin (ops only) -------------------------------------------------
    path("admin/", admin.site.urls),
    # --- API v1 -----------------------------------------------------------
    path("api/v1/auth/", include("contexts.identity.api.urls")),
    path("api/v1/catalog/", include("contexts.catalog.api.urls")),
    path("api/v1/features/", include("contexts.features.api.urls")),
    path("api/v1/notifications/", include("contexts.notifications.api.urls")),
    path("api/v1/storage/", include("shared.infrastructure.storage.api.urls")),
    path("api/v1/search/", include("contexts.search.api.urls")),
    path("api/v1/employees/", include("contexts.employees.api.urls")),
    path("api/v1/customers/", include("contexts.customers.api.urls")),
    path("api/v1/inventory/", include("contexts.inventory.api.urls")),
    path("api/v1/restaurant/", include("contexts.restaurant.api.urls")),
    path("api/v1/ordering/", include("contexts.ordering.api.urls")),
    # path("", include("interface.web.urls")),
    path("auth/", include("contexts.identity.urls")),
    path("auth/", include("contexts.tenants.urls")),
    path("dashboard/catalog/", include("contexts.catalog.urls")),
    path("dashboard/restaurant/", include("contexts.restaurant.urls")),
    path("dashboard/staff/", include("contexts.employees.urls")),
    path("inventory/", include("contexts.inventory.urls")),
    path("pos/", include("contexts.ordering.urls")),
    path("dashboard/", include("contexts.reporting.urls")),
    path("billing/", include("contexts.reporting.urls_billing")),
    path("", include("contexts.marketing.urls")),
    path("styleguide/", TemplateView.as_view(template_name="styleguide.html"), name="styleguide"),
    path("platform/", include("contexts.super_admin.urls")),
    
    # Phase 4 Previews
    path("preview/customers/", TemplateView.as_view(template_name="customers/customer_list.html"), name="preview_customers"),

    # Phase 7 Previews
    # Removed kds preview as it is now live at /pos/kds/

    # Phase 8 Previews
    path("preview/inventory/", TemplateView.as_view(template_name="inventory/inventory_list.html"), name="preview_inventory"),
    path("preview/transfers/", TemplateView.as_view(template_name="inventory/transfer_list.html"), name="preview_transfers"),
    path("preview/settings/", TemplateView.as_view(template_name="tenants/settings.html"), name="preview_settings"),
    path("preview/billing/", TemplateView.as_view(template_name="billing/billing.html"), name="preview_billing"),
]

if "django_prometheus" in settings.INSTALLED_APPS:
    from shared.infrastructure.monitoring.views import metrics_view
    urlpatterns += [
        path("metrics/", metrics_view, name="prometheus-metrics"),
    ]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
