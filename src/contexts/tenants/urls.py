from django.urls import path
from contexts.tenants import views

app_name = "tenants"

urlpatterns = [
    path("select-tenant/", views.TenantSelectView.as_view(), name="select_tenant"),
    path("set-tenant/<slug:slug>/", views.SetTenantView.as_view(), name="set_tenant"),
    path("set-tenant/uuid/<uuid:pk>/", views.SetTenantUUIDView.as_view(), name="set_tenant_uuid"),
]
