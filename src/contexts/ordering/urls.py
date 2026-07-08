from django.urls import path
from contexts.ordering import views

app_name = "ordering"

urlpatterns = [
    path("", views.POSMainView.as_view(), name="pos_main"),
    path("<uuid:tenant_id>/", views.POSMainView.as_view(), name="pos_main_tenant"),
    path("products/", views.POSProductGridView.as_view(), name="pos_product_grid"),
    path("<uuid:tenant_id>/products/", views.POSProductGridView.as_view(), name="pos_product_grid_tenant"),
    path("categories/ribbon/", views.POSCategoryRibbonView.as_view(), name="pos_category_ribbon"),
    path("<uuid:tenant_id>/categories/ribbon/", views.POSCategoryRibbonView.as_view(), name="pos_category_ribbon_tenant"),
    path("cart/add/<uuid:product_id>/", views.POSAddToCartView.as_view(), name="pos_add_to_cart"),
    path("<uuid:tenant_id>/cart/add/<uuid:product_id>/", views.POSAddToCartView.as_view(), name="pos_add_to_cart_tenant"),
    path("cart/add-custom/<uuid:product_id>/", views.POSAddWithModifiersView.as_view(), name="pos_add_with_modifiers"),
    path("<uuid:tenant_id>/cart/add-custom/<uuid:product_id>/", views.POSAddWithModifiersView.as_view(), name="pos_add_with_modifiers_tenant"),
    path("pos/product/<uuid:product_id>/modifiers/", views.POSModifierModalView.as_view(), name="pos_modifier_modal"),
    path("<uuid:tenant_id>/pos/product/<uuid:product_id>/modifiers/", views.POSModifierModalView.as_view(), name="pos_modifier_modal_tenant"),
    path("pos/combo/<uuid:combo_id>/", views.POSComboModalView.as_view(), name="pos_combo_modal"),
    path("<uuid:tenant_id>/pos/combo/<uuid:combo_id>/", views.POSComboModalView.as_view(), name="pos_combo_modal_tenant"),
    path("pos/item/<uuid:item_id>/modifiers/", views.POSCartEditModifierModalView.as_view(), name="pos_edit_modifier_modal"),
    path("<uuid:tenant_id>/pos/item/<uuid:item_id>/modifiers/", views.POSCartEditModifierModalView.as_view(), name="pos_edit_modifier_modal_tenant"),
    path("cart/update/<uuid:item_id>/<str:action>/", views.POSUpdateItemView.as_view(), name="pos_update_item"),
    path("<uuid:tenant_id>/cart/update/<uuid:item_id>/<str:action>/", views.POSUpdateItemView.as_view(), name="pos_update_item_tenant"),
    path("cart/remove/<uuid:item_id>/", views.POSRemoveItemView.as_view(), name="pos_remove_item"),
    path("<uuid:tenant_id>/cart/remove/<uuid:item_id>/", views.POSRemoveItemView.as_view(), name="pos_remove_item_tenant"),
    path("cart/remove-combo/<uuid:combo_id>/", views.POSRemoveComboView.as_view(), name="pos_remove_combo"),
    path("<uuid:tenant_id>/cart/remove-combo/<uuid:combo_id>/", views.POSRemoveComboView.as_view(), name="pos_remove_combo_tenant"),
    path("cart/clear/", views.POSClearCartView.as_view(), name="pos_clear_cart"),
    path("<uuid:tenant_id>/cart/clear/", views.POSClearCartView.as_view(), name="pos_clear_cart_tenant"),
    path("cart/save/", views.POSSaveOrderView.as_view(), name="pos_save_order"),
    path("<uuid:tenant_id>/cart/save/", views.POSSaveOrderView.as_view(), name="pos_save_order_tenant"),
    path("pos/modal/checkout/", views.POSCheckoutModalView.as_view(), name="pos_checkout_modal"),
    path("<uuid:tenant_id>/pos/modal/checkout/", views.POSCheckoutModalView.as_view(), name="pos_checkout_modal_tenant"),
    
    # NEW: Retrospective discounts
    path("pos/modal/discount/", views.POSDiscountModalView.as_view(), name="pos_discount_modal"),
    path("<uuid:tenant_id>/pos/modal/discount/", views.POSDiscountModalView.as_view(), name="pos_discount_modal_tenant"),
    path("pos/apply-combo/<uuid:combo_id>/", views.POSApplyComboView.as_view(), name="pos_apply_combo"),
    path("<uuid:tenant_id>/pos/apply-combo/<uuid:combo_id>/", views.POSApplyComboView.as_view(), name="pos_apply_combo_tenant"),

    path("checkout/process/", views.POSProcessPaymentView.as_view(), name="pos_process_payment"),
    path("<uuid:tenant_id>/checkout/process/", views.POSProcessPaymentView.as_view(), name="pos_process_payment_tenant"),
    
    # KDS Endpoints
    path("kds/", views.KDSMainView.as_view(), name="kds_main"),
    path("<uuid:tenant_id>/kds/", views.KDSMainView.as_view(), name="kds_main_tenant"),
    path("kds/tickets/", views.KDSTicketListView.as_view(), name="kds_ticket_list"),
    path("<uuid:tenant_id>/kds/tickets/", views.KDSTicketListView.as_view(), name="kds_ticket_list_tenant"),
    path("kds/update/<uuid:kot_id>/<str:status>/", views.KDSUpdateStatusView.as_view(), name="kds_update_status"),
    path("<uuid:tenant_id>/kds/update/<uuid:kot_id>/<str:status>/", views.KDSUpdateStatusView.as_view(), name="kds_update_status_tenant"),
    path("kds/item/<uuid:item_id>/bump/", views.KDSBumpItemView.as_view(), name="kds_bump_item"),
    path("<uuid:tenant_id>/kds/item/<uuid:item_id>/bump/", views.KDSBumpItemView.as_view(), name="kds_bump_item_tenant"),
    
    # Table Management
    path("tables/", views.POSTableMainView.as_view(), name="pos_tables_main"),
    path("<uuid:tenant_id>/tables/", views.POSTableMainView.as_view(), name="pos_tables_main_tenant"),
    path("tables/action/<uuid:table_id>/", views.POSTableActionView.as_view(), name="pos_table_action"),
    path("<uuid:tenant_id>/tables/action/<uuid:table_id>/", views.POSTableActionView.as_view(), name="pos_table_action_tenant"),
    path("tables/map/", views.POSTableMapView.as_view(), name="pos_table_map"),
    path("<uuid:tenant_id>/tables/map/", views.POSTableMapView.as_view(), name="pos_table_map_tenant"),
    path("tables/select/<uuid:table_id>/", views.POSSelectTableView.as_view(), name="pos_select_table"),
    path("<uuid:tenant_id>/tables/select/<uuid:table_id>/", views.POSSelectTableView.as_view(), name="pos_select_table_tenant"),
    path("tables/transfer/<uuid:source_table_id>/<uuid:target_table_id>/", views.TableTransferView.as_view(), name="pos_transfer_table"),
    path("<uuid:tenant_id>/tables/transfer/<uuid:source_table_id>/<uuid:target_table_id>/", views.TableTransferView.as_view(), name="pos_transfer_table_tenant"),
    path("tables/transfer/modal/<uuid:table_id>/", views.TransferTableModalView.as_view(), name="pos_transfer_table_modal"),
    path("<uuid:tenant_id>/tables/transfer/modal/<uuid:table_id>/", views.TransferTableModalView.as_view(), name="pos_transfer_table_modal_tenant"),
    
    # Print Queue
    path("print-queue/", views.PrintQueueView.as_view(), name="print_queue"),
    path("<uuid:tenant_id>/print-queue/", views.PrintQueueView.as_view(), name="print_queue_tenant"),
    path("print-queue/reprint/<uuid:job_id>/", views.ManualReprintView.as_view(), name="manual_reprint"),
    path("<uuid:tenant_id>/print-queue/reprint/<uuid:job_id>/", views.ManualReprintView.as_view(), name="manual_reprint_tenant"),
]
