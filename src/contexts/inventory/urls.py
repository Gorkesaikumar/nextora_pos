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
    path("<uuid:tenant_id>/", views.InventoryItemListView.as_view(), name="item_list_tenant"),
    path("items/create/", views.InventoryItemCreateView.as_view(), name="item_create"),
    path("<uuid:tenant_id>/items/create/", views.InventoryItemCreateView.as_view(), name="item_create_tenant"),
    path("items/<uuid:pk>/edit/", views.InventoryItemUpdateView.as_view(), name="item_update"),
    path("<uuid:tenant_id>/items/<uuid:pk>/edit/", views.InventoryItemUpdateView.as_view(), name="item_update_tenant"),

    # Suppliers
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("<uuid:tenant_id>/suppliers/", views.SupplierListView.as_view(), name="supplier_list_tenant"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("<uuid:tenant_id>/suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create_tenant"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("<uuid:tenant_id>/suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update_tenant"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),
    path("<uuid:tenant_id>/suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete_tenant"),

    # Purchase orders
    path("purchases/", views.PurchaseOrderListView.as_view(), name="purchase_list"),
    path("<uuid:tenant_id>/purchases/", views.PurchaseOrderListView.as_view(), name="purchase_list_tenant"),
    path("purchases/create/", views.PurchaseOrderCreateView.as_view(), name="purchase_create"),
    path("<uuid:tenant_id>/purchases/create/", views.PurchaseOrderCreateView.as_view(), name="purchase_create_tenant"),
    path("purchases/<uuid:pk>/", views.PurchaseOrderDetailView.as_view(), name="purchase_detail"),
    path("<uuid:tenant_id>/purchases/<uuid:pk>/", views.PurchaseOrderDetailView.as_view(), name="purchase_detail_tenant"),
    path("purchases/<uuid:pk>/receive/", views.PurchaseOrderReceiveView.as_view(), name="purchase_receive"),
    path("<uuid:tenant_id>/purchases/<uuid:pk>/receive/", views.PurchaseOrderReceiveView.as_view(), name="purchase_receive_tenant"),

    # Stock adjustments
    path("adjustments/", views.StockAdjustmentListView.as_view(), name="adjustment_list"),
    path("<uuid:tenant_id>/adjustments/", views.StockAdjustmentListView.as_view(), name="adjustment_list_tenant"),
    path("adjustments/create/", views.StockAdjustmentCreateView.as_view(), name="adjustment_create"),
    path("<uuid:tenant_id>/adjustments/create/", views.StockAdjustmentCreateView.as_view(), name="adjustment_create_tenant"),
    path("adjustments/<uuid:pk>/approve/", views.StockAdjustmentApproveView.as_view(), name="adjustment_approve"),
    path("<uuid:tenant_id>/adjustments/<uuid:pk>/approve/", views.StockAdjustmentApproveView.as_view(), name="adjustment_approve_tenant"),
]
