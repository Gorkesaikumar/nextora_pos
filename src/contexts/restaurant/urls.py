from django.urls import path
from contexts.restaurant import views

app_name = "restaurant"

urlpatterns = [
    path("branches/", views.BranchListView.as_view(), name="branch_list"),
    path("branches/create/", views.BranchCreateView.as_view(), name="branch_create"),
    path("branches/<uuid:pk>/edit/", views.BranchUpdateView.as_view(), name="branch_update"),
    path("branches/<uuid:pk>/delete/", views.BranchDeleteView.as_view(), name="branch_delete"),
    path("branches/<uuid:pk>/archive/", views.BranchArchiveView.as_view(), name="branch_archive"),
    path("branches/<uuid:pk>/status/", views.BranchToggleStatusView.as_view(), name="branch_toggle_status"),
    path("branches/<uuid:pk>/default/", views.BranchSetDefaultView.as_view(), name="branch_set_default"),
    
    path("printers/", views.PrinterListView.as_view(), name="printer_list"),
    path("printers/create/", views.PrinterCreateView.as_view(), name="printer_create"),
    path("printers/<uuid:pk>/edit/", views.PrinterUpdateView.as_view(), name="printer_update"),
    path("printers/<uuid:pk>/delete/", views.PrinterDeleteView.as_view(), name="printer_delete"),
    path("printers/<uuid:pk>/test/", views.PrinterTestPrintView.as_view(), name="printer_test"),

    path("tables/", views.TableListView.as_view(), name="table_list"),
    path("tables/create/", views.TableCreateView.as_view(), name="table_create"),
    path("tables/<uuid:pk>/edit/", views.TableUpdateView.as_view(), name="table_update"),
    path("tables/<uuid:pk>/delete/", views.TableDeleteView.as_view(), name="table_delete"),
    path("analytics/", views.TableAnalyticsView.as_view(), name="table_analytics"),
    path("tables/<uuid:table_id>/qr/", views.TableQRModalView.as_view(), name="table_qr_modal"),
]
