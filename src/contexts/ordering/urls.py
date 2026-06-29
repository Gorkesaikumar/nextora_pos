from django.urls import path
from contexts.ordering import views

app_name = "ordering"

urlpatterns = [
    path("", views.POSMainView.as_view(), name="pos_main"),
    path("products/", views.POSProductGridView.as_view(), name="pos_product_grid"),
    path("categories/ribbon/", views.POSCategoryRibbonView.as_view(), name="pos_category_ribbon"),
    path("cart/add/<uuid:product_id>/", views.POSAddToCartView.as_view(), name="pos_add_to_cart"),
    path("cart/update/<uuid:item_id>/<str:action>/", views.POSUpdateItemView.as_view(), name="pos_update_item"),
    path("cart/remove/<uuid:item_id>/", views.POSRemoveItemView.as_view(), name="pos_remove_item"),
    path("cart/clear/", views.POSClearCartView.as_view(), name="pos_clear_cart"),
    path("cart/save/", views.POSSaveOrderView.as_view(), name="pos_save_order"),
    path("checkout/modal/", views.POSCheckoutModalView.as_view(), name="pos_checkout_modal"),
    path("checkout/process/", views.POSProcessPaymentView.as_view(), name="pos_process_payment"),
    
    # KDS Endpoints
    path("kds/", views.KDSMainView.as_view(), name="kds_main"),
    path("kds/tickets/", views.KDSTicketListView.as_view(), name="kds_ticket_list"),
    path("kds/update/<uuid:kot_id>/<str:status>/", views.KDSUpdateStatusView.as_view(), name="kds_update_status"),
    
    # Table Management
    path("tables/", views.POSTableMainView.as_view(), name="pos_tables_main"),
    path("tables/action/<uuid:table_id>/", views.POSTableActionView.as_view(), name="pos_table_action"),
    path("tables/map/", views.POSTableMapView.as_view(), name="pos_table_map"),
    path("tables/select/<uuid:table_id>/", views.POSSelectTableView.as_view(), name="pos_select_table"),
    path("tables/transfer/<uuid:source_table_id>/<uuid:target_table_id>/", views.TableTransferView.as_view(), name="pos_transfer_table"),
    path("tables/transfer/modal/<uuid:table_id>/", views.TransferTableModalView.as_view(), name="pos_transfer_table_modal"),
]
