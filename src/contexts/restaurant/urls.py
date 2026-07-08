from django.urls import path
from contexts.restaurant import views

app_name = "restaurant"

urlpatterns = [
    path("branches/", views.BranchListView.as_view(), name="branch_list"),
    path("<uuid:tenant_id>/branches/", views.BranchListView.as_view(), name="branch_list_tenant"),
    path("branches/create/", views.BranchCreateView.as_view(), name="branch_create"),
    path("<uuid:tenant_id>/branches/create/", views.BranchCreateView.as_view(), name="branch_create_tenant"),
    path("branches/<uuid:pk>/edit/", views.BranchUpdateView.as_view(), name="branch_update"),
    path("<uuid:tenant_id>/branches/<uuid:pk>/edit/", views.BranchUpdateView.as_view(), name="branch_update_tenant"),
    path("branches/<uuid:pk>/delete/", views.BranchDeleteView.as_view(), name="branch_delete"),
    path("<uuid:tenant_id>/branches/<uuid:pk>/delete/", views.BranchDeleteView.as_view(), name="branch_delete_tenant"),
    path("branches/<uuid:pk>/archive/", views.BranchArchiveView.as_view(), name="branch_archive"),
    path("<uuid:tenant_id>/branches/<uuid:pk>/archive/", views.BranchArchiveView.as_view(), name="branch_archive_tenant"),
    path("branches/<uuid:pk>/status/", views.BranchToggleStatusView.as_view(), name="branch_toggle_status"),
    path("<uuid:tenant_id>/branches/<uuid:pk>/status/", views.BranchToggleStatusView.as_view(), name="branch_toggle_status_tenant"),
    path("branches/<uuid:pk>/default/", views.BranchSetDefaultView.as_view(), name="branch_set_default"),
    path("<uuid:tenant_id>/branches/<uuid:pk>/default/", views.BranchSetDefaultView.as_view(), name="branch_set_default_tenant"),
    
    path("printers/", views.PrinterListView.as_view(), name="printer_list"),
    path("<uuid:tenant_id>/printers/", views.PrinterListView.as_view(), name="printer_list_tenant"),
    path("printers/create/", views.PrinterCreateView.as_view(), name="printer_create"),
    path("<uuid:tenant_id>/printers/create/", views.PrinterCreateView.as_view(), name="printer_create_tenant"),
    path("printers/<uuid:pk>/edit/", views.PrinterUpdateView.as_view(), name="printer_update"),
    path("<uuid:tenant_id>/printers/<uuid:pk>/edit/", views.PrinterUpdateView.as_view(), name="printer_update_tenant"),
    path("printers/<uuid:pk>/delete/", views.PrinterDeleteView.as_view(), name="printer_delete"),
    path("<uuid:tenant_id>/printers/<uuid:pk>/delete/", views.PrinterDeleteView.as_view(), name="printer_delete_tenant"),
    path("printers/<uuid:pk>/test/", views.PrinterTestPrintView.as_view(), name="printer_test"),
    path("<uuid:tenant_id>/printers/<uuid:pk>/test/", views.PrinterTestPrintView.as_view(), name="printer_test_tenant"),

    path("tables/", views.TableListView.as_view(), name="table_list"),
    path("<uuid:tenant_id>/tables/", views.TableListView.as_view(), name="table_list_tenant"),
    path("tables/create/", views.TableCreateView.as_view(), name="table_create"),
    path("<uuid:tenant_id>/tables/create/", views.TableCreateView.as_view(), name="table_create_tenant"),
    path("tables/<uuid:pk>/edit/", views.TableUpdateView.as_view(), name="table_update"),
    path("<uuid:tenant_id>/tables/<uuid:pk>/edit/", views.TableUpdateView.as_view(), name="table_update_tenant"),
    path("tables/<uuid:pk>/delete/", views.TableDeleteView.as_view(), name="table_delete"),
    path("<uuid:tenant_id>/tables/<uuid:pk>/delete/", views.TableDeleteView.as_view(), name="table_delete_tenant"),
    path("analytics/", views.TableAnalyticsView.as_view(), name="table_analytics"),
    path("<uuid:tenant_id>/analytics/", views.TableAnalyticsView.as_view(), name="table_analytics_tenant"),
    path("tables/<uuid:table_id>/qr/", views.TableQRModalView.as_view(), name="table_qr_modal"),
    path("<uuid:tenant_id>/tables/<uuid:table_id>/qr/", views.TableQRModalView.as_view(), name="table_qr_modal_tenant"),
]
