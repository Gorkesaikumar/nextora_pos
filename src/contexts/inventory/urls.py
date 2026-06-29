"""Inventory web (server-rendered) URL routing.

Mounted at ``/inventory/`` (see config/urls.py). The REST surface lives
separately under ``/api/v1/inventory/`` via ``inventory.api.urls``.
"""
from django.urls import path

from contexts.inventory import views

app_name = "inventory"

urlpatterns = [
    # Inventory items (stock records)
    path("", views.InventoryItemListView.as_view(), name="item_list"),
    path("items/create/", views.InventoryItemCreateView.as_view(), name="item_create"),
    path("items/<uuid:pk>/edit/", views.InventoryItemUpdateView.as_view(), name="item_update"),

    # Suppliers
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),

    # Purchase orders
    path("purchases/", views.PurchaseOrderListView.as_view(), name="purchase_list"),
    path("purchases/create/", views.PurchaseOrderCreateView.as_view(), name="purchase_create"),
    path("purchases/<uuid:pk>/", views.PurchaseOrderDetailView.as_view(), name="purchase_detail"),
    path("purchases/<uuid:pk>/receive/", views.PurchaseOrderReceiveView.as_view(), name="purchase_receive"),

    # Stock adjustments
    path("adjustments/", views.StockAdjustmentListView.as_view(), name="adjustment_list"),
    path("adjustments/create/", views.StockAdjustmentCreateView.as_view(), name="adjustment_create"),
    path("adjustments/<uuid:pk>/approve/", views.StockAdjustmentApproveView.as_view(), name="adjustment_approve"),
]
