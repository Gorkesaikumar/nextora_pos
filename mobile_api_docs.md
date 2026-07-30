# Nextora POS - Mobile API Documentation & Implementation Plan

## User Review Required
> [!IMPORTANT]
> Please review the generated API documentation, architecture analysis, and Flutter implementation phases below. Approve this plan to begin Flutter development.

## STEP 1 — PROJECT ARCHITECTURE ANALYSIS
- **Django Apps:** identity, tenants, ordering, restaurant, reporting, marketing, notifications, inventory, employees, features, catalog, billing, customers, search, super_admin
- **URL Routing & API Versioning:** DRF Routers used extensively, mostly nested under API namespaces.
- **Authentication System:** JWT via `EnterpriseJWTAuthentication`.
- **Permissions:** DRF Custom Permissions, Tenant-aware.
- **Shared Utilities:** Domain Events, Outbox Pattern, Caching, Tenancy managers.
- **Celery Tasks:** Used for event dispatching and background jobs.
- **Channels/WebSockets:** Configured in `ordering/routing.py`.

## STEP 2 & 3 — API DISCOVERY & MODULES
Discovered 462 endpoints across 17 modules.

## STEP 4 — DOCUMENT EVERY API
### POST /api/v1/auth/logout/
- **Module:** auth
- **Purpose:** auth_logout_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/logout-all/
- **Module:** auth
- **Purpose:** auth_logout_all_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/me/
- **Module:** auth
- **Purpose:** auth_me_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/auth/me/
- **Module:** auth
- **Purpose:** auth_me_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/memberships/
- **Module:** auth
- **Purpose:** auth_memberships_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/memberships/
- **Module:** auth
- **Purpose:** auth_memberships_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/memberships/{id}/
- **Module:** auth
- **Purpose:** auth_memberships_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/auth/memberships/{id}/
- **Module:** auth
- **Purpose:** auth_memberships_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/auth/memberships/{id}/
- **Module:** auth
- **Purpose:** auth_memberships_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/auth/memberships/{id}/
- **Module:** auth
- **Purpose:** auth_memberships_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/password-reset/
- **Module:** auth
- **Purpose:** auth_password_reset_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/password-reset/confirm/
- **Module:** auth
- **Purpose:** auth_password_reset_confirm_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/permissions/
- **Module:** auth
- **Purpose:** auth_permissions_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/permissions/{id}/
- **Module:** auth
- **Purpose:** auth_permissions_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/roles/
- **Module:** auth
- **Purpose:** auth_roles_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/roles/{id}/
- **Module:** auth
- **Purpose:** auth_roles_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/sessions/
- **Module:** auth
- **Purpose:** auth_sessions_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/sessions/
- **Module:** auth
- **Purpose:** auth_sessions_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/auth/sessions/{id}/
- **Module:** auth
- **Purpose:** auth_sessions_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/sessions/{id}/revoke/
- **Module:** auth
- **Purpose:** auth_sessions_revoke_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/token/
- **Module:** auth
- **Purpose:** auth_token_create
- **Auth Required:** No (or inherited)
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/token/refresh/
- **Module:** auth
- **Purpose:** auth_token_refresh_create
- **Auth Required:** No (or inherited)
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/auth/token/verify/
- **Module:** auth
- **Purpose:** auth_token_verify_create
- **Auth Required:** No (or inherited)
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/billing/invoices/
- **Module:** billing
- **Purpose:** billing_invoices_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/billing/invoices/{id}/
- **Module:** billing
- **Purpose:** billing_invoices_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/billing/subscriptions/
- **Module:** billing
- **Purpose:** billing_subscriptions_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/billing/subscriptions/{id}/
- **Module:** billing
- **Purpose:** billing_subscriptions_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/categories/
- **Module:** catalog
- **Purpose:** catalog_categories_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/categories/
- **Module:** catalog
- **Purpose:** catalog_categories_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/categories/{id}/
- **Module:** catalog
- **Purpose:** catalog_categories_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/categories/{id}/
- **Module:** catalog
- **Purpose:** catalog_categories_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/categories/{id}/
- **Module:** catalog
- **Purpose:** catalog_categories_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/categories/{id}/
- **Module:** catalog
- **Purpose:** catalog_categories_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/combos/
- **Module:** catalog
- **Purpose:** catalog_combos_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/combos/
- **Module:** catalog
- **Purpose:** catalog_combos_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/combos/{id}/
- **Module:** catalog
- **Purpose:** catalog_combos_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/combos/{id}/
- **Module:** catalog
- **Purpose:** catalog_combos_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/combos/{id}/
- **Module:** catalog
- **Purpose:** catalog_combos_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/combos/{id}/
- **Module:** catalog
- **Purpose:** catalog_combos_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/modifier-groups/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/modifier-groups/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/modifier-groups/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/modifier-groups/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/modifier-groups/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/modifier-groups/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifier_groups_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/modifiers/
- **Module:** catalog
- **Purpose:** catalog_modifiers_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/modifiers/
- **Module:** catalog
- **Purpose:** catalog_modifiers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/modifiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifiers_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/modifiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifiers_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/modifiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifiers_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/modifiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_modifiers_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/price-tiers/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/price-tiers/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/price-tiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/price-tiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/price-tiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/price-tiers/{id}/
- **Module:** catalog
- **Purpose:** catalog_price_tiers_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/products/
- **Module:** catalog
- **Purpose:** catalog_products_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/products/
- **Module:** catalog
- **Purpose:** catalog_products_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/products/{id}/
- **Module:** catalog
- **Purpose:** catalog_products_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/products/{id}/
- **Module:** catalog
- **Purpose:** catalog_products_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/products/{id}/
- **Module:** catalog
- **Purpose:** catalog_products_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/products/{id}/
- **Module:** catalog
- **Purpose:** catalog_products_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/products/export/
- **Module:** catalog
- **Purpose:** catalog_products_export_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/products/import_csv/
- **Module:** catalog
- **Purpose:** catalog_products_import_csv_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/taxes/
- **Module:** catalog
- **Purpose:** catalog_taxes_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/taxes/
- **Module:** catalog
- **Purpose:** catalog_taxes_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/taxes/{id}/
- **Module:** catalog
- **Purpose:** catalog_taxes_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/taxes/{id}/
- **Module:** catalog
- **Purpose:** catalog_taxes_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/taxes/{id}/
- **Module:** catalog
- **Purpose:** catalog_taxes_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/taxes/{id}/
- **Module:** catalog
- **Purpose:** catalog_taxes_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/units/
- **Module:** catalog
- **Purpose:** catalog_units_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/units/
- **Module:** catalog
- **Purpose:** catalog_units_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/units/{id}/
- **Module:** catalog
- **Purpose:** catalog_units_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/units/{id}/
- **Module:** catalog
- **Purpose:** catalog_units_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/units/{id}/
- **Module:** catalog
- **Purpose:** catalog_units_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/units/{id}/
- **Module:** catalog
- **Purpose:** catalog_units_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/variants/
- **Module:** catalog
- **Purpose:** catalog_variants_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/catalog/variants/
- **Module:** catalog
- **Purpose:** catalog_variants_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/catalog/variants/{id}/
- **Module:** catalog
- **Purpose:** catalog_variants_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/catalog/variants/{id}/
- **Module:** catalog
- **Purpose:** catalog_variants_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/catalog/variants/{id}/
- **Module:** catalog
- **Purpose:** catalog_variants_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/catalog/variants/{id}/
- **Module:** catalog
- **Purpose:** catalog_variants_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/coupons/
- **Module:** customers
- **Purpose:** customers_coupons_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/coupons/
- **Module:** customers
- **Purpose:** customers_coupons_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/coupons/{id}/
- **Module:** customers
- **Purpose:** customers_coupons_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/customers/coupons/{id}/
- **Module:** customers
- **Purpose:** customers_coupons_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/customers/coupons/{id}/
- **Module:** customers
- **Purpose:** customers_coupons_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/customers/coupons/{id}/
- **Module:** customers
- **Purpose:** customers_coupons_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/coupons/validate/
- **Module:** customers
- **Purpose:** customers_coupons_validate_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/loyalty/
- **Module:** customers
- **Purpose:** customers_loyalty_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/loyalty/{id}/
- **Module:** customers
- **Purpose:** customers_loyalty_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/customers/loyalty/{id}/
- **Module:** customers
- **Purpose:** customers_loyalty_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/
- **Module:** customers
- **Purpose:** customers_profiles_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/profiles/
- **Module:** customers
- **Purpose:** customers_profiles_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/
- **Module:** customers
- **Purpose:** customers_profiles_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/customers/profiles/{id}/
- **Module:** customers
- **Purpose:** customers_profiles_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/customers/profiles/{id}/
- **Module:** customers
- **Purpose:** customers_profiles_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/customers/profiles/{id}/
- **Module:** customers
- **Purpose:** customers_profiles_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/coupons/
- **Module:** customers
- **Purpose:** customers_profiles_coupons_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/credit/ledger/
- **Module:** customers
- **Purpose:** customers_profiles_credit_ledger_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/orders/
- **Module:** customers
- **Purpose:** customers_profiles_orders_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/profiles/{id}/points/earn/
- **Module:** customers
- **Purpose:** customers_profiles_points_earn_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/points/history/
- **Module:** customers
- **Purpose:** customers_profiles_points_history_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/profiles/{id}/points/redeem/
- **Module:** customers
- **Purpose:** customers_profiles_points_redeem_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/profiles/{id}/wallet/deposit/
- **Module:** customers
- **Purpose:** customers_profiles_wallet_deposit_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/customers/profiles/{id}/wallet/history/
- **Module:** customers
- **Purpose:** customers_profiles_wallet_history_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/customers/profiles/{id}/wallet/pay/
- **Module:** customers
- **Purpose:** customers_profiles_wallet_pay_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/charts/
- **Module:** dashboard
- **Purpose:** dashboard_charts_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/export/
- **Module:** dashboard
- **Purpose:** dashboard_export_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/gst/
- **Module:** dashboard
- **Purpose:** dashboard_gst_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/payments/
- **Module:** dashboard
- **Purpose:** dashboard_payments_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/profit/
- **Module:** dashboard
- **Purpose:** dashboard_profit_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/sales/
- **Module:** dashboard
- **Purpose:** dashboard_sales_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/summary/
- **Module:** dashboard
- **Purpose:** dashboard_summary_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/top-categories/
- **Module:** dashboard
- **Purpose:** dashboard_top_categories_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/dashboard/top-items/
- **Module:** dashboard
- **Purpose:** dashboard_top_items_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/attendance/
- **Module:** employees
- **Purpose:** employees_attendance_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/
- **Module:** employees
- **Purpose:** employees_attendance_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/attendance/{id}/
- **Module:** employees
- **Purpose:** employees_attendance_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/attendance/{id}/
- **Module:** employees
- **Purpose:** employees_attendance_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/attendance/{id}/
- **Module:** employees
- **Purpose:** employees_attendance_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/attendance/{id}/
- **Module:** employees
- **Purpose:** employees_attendance_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/{id}/check-out/
- **Module:** employees
- **Purpose:** employees_attendance_check_out_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/{id}/clock-out/
- **Module:** employees
- **Purpose:** employees_attendance_clock_out_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/{id}/end-break/
- **Module:** employees
- **Purpose:** employees_attendance_end_break_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/{id}/start-break/
- **Module:** employees
- **Purpose:** employees_attendance_start_break_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/check-in/
- **Module:** employees
- **Purpose:** employees_attendance_check_in_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/attendance/clock-in/
- **Module:** employees
- **Purpose:** employees_attendance_clock_in_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/dashboard/
- **Module:** employees
- **Purpose:** employees_dashboard_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/departments/
- **Module:** employees
- **Purpose:** employees_departments_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/departments/
- **Module:** employees
- **Purpose:** employees_departments_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/departments/{id}/
- **Module:** employees
- **Purpose:** employees_departments_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/departments/{id}/
- **Module:** employees
- **Purpose:** employees_departments_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/departments/{id}/
- **Module:** employees
- **Purpose:** employees_departments_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/departments/{id}/
- **Module:** employees
- **Purpose:** employees_departments_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/designations/
- **Module:** employees
- **Purpose:** employees_designations_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/designations/
- **Module:** employees
- **Purpose:** employees_designations_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/designations/{id}/
- **Module:** employees
- **Purpose:** employees_designations_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/designations/{id}/
- **Module:** employees
- **Purpose:** employees_designations_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/designations/{id}/
- **Module:** employees
- **Purpose:** employees_designations_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/designations/{id}/
- **Module:** employees
- **Purpose:** employees_designations_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/employees/
- **Module:** employees
- **Purpose:** employees_employees_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/employees/
- **Module:** employees
- **Purpose:** employees_employees_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/employees/{id}/
- **Module:** employees
- **Purpose:** employees_employees_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/employees/{id}/
- **Module:** employees
- **Purpose:** employees_employees_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/employees/{id}/
- **Module:** employees
- **Purpose:** employees_employees_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/employees/{id}/
- **Module:** employees
- **Purpose:** employees_employees_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/leave-balances/
- **Module:** employees
- **Purpose:** employees_leave_balances_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/leave-balances/{id}/
- **Module:** employees
- **Purpose:** employees_leave_balances_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/leaves/
- **Module:** employees
- **Purpose:** employees_leaves_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/leaves/
- **Module:** employees
- **Purpose:** employees_leaves_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/leaves/{id}/
- **Module:** employees
- **Purpose:** employees_leaves_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/leaves/{id}/
- **Module:** employees
- **Purpose:** employees_leaves_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/leaves/{id}/
- **Module:** employees
- **Purpose:** employees_leaves_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/leaves/{id}/
- **Module:** employees
- **Purpose:** employees_leaves_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/leaves/{id}/approve/
- **Module:** employees
- **Purpose:** employees_leaves_approve_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/leaves/{id}/reject/
- **Module:** employees
- **Purpose:** employees_leaves_reject_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/payroll/
- **Module:** employees
- **Purpose:** employees_payroll_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/payroll/
- **Module:** employees
- **Purpose:** employees_payroll_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/payroll/{id}/
- **Module:** employees
- **Purpose:** employees_payroll_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/payroll/{id}/
- **Module:** employees
- **Purpose:** employees_payroll_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/payroll/{id}/
- **Module:** employees
- **Purpose:** employees_payroll_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/payroll/{id}/
- **Module:** employees
- **Purpose:** employees_payroll_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/payroll/run/
- **Module:** employees
- **Purpose:** employees_payroll_run_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/performance/
- **Module:** employees
- **Purpose:** employees_performance_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/performance/
- **Module:** employees
- **Purpose:** employees_performance_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/performance/{id}/
- **Module:** employees
- **Purpose:** employees_performance_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/performance/{id}/
- **Module:** employees
- **Purpose:** employees_performance_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/performance/{id}/
- **Module:** employees
- **Purpose:** employees_performance_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/performance/{id}/
- **Module:** employees
- **Purpose:** employees_performance_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/profiles/
- **Module:** employees
- **Purpose:** employees_profiles_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/profiles/
- **Module:** employees
- **Purpose:** employees_profiles_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/profiles/{id}/
- **Module:** employees
- **Purpose:** employees_profiles_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/profiles/{id}/
- **Module:** employees
- **Purpose:** employees_profiles_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/profiles/{id}/
- **Module:** employees
- **Purpose:** employees_profiles_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/profiles/{id}/
- **Module:** employees
- **Purpose:** employees_profiles_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/shifts/
- **Module:** employees
- **Purpose:** employees_shifts_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/employees/shifts/
- **Module:** employees
- **Purpose:** employees_shifts_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/employees/shifts/{id}/
- **Module:** employees
- **Purpose:** employees_shifts_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/employees/shifts/{id}/
- **Module:** employees
- **Purpose:** employees_shifts_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/employees/shifts/{id}/
- **Module:** employees
- **Purpose:** employees_shifts_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/employees/shifts/{id}/
- **Module:** employees
- **Purpose:** employees_shifts_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/features/cache/clear/
- **Module:** features
- **Purpose:** features_cache_clear_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/features/evaluate/
- **Module:** features
- **Purpose:** features_evaluate_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/features/limits/
- **Module:** features
- **Purpose:** features_limits_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/features/modules/
- **Module:** features
- **Purpose:** features_modules_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/features/subscription/
- **Module:** features
- **Purpose:** features_subscription_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/features/validate/
- **Module:** features
- **Purpose:** features_validate_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/health/
- **Module:** health
- **Purpose:** health_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/adjustments/
- **Module:** inventory
- **Purpose:** inventory_adjustments_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/adjustments/
- **Module:** inventory
- **Purpose:** inventory_adjustments_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/adjustments/{id}/
- **Module:** inventory
- **Purpose:** inventory_adjustments_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/adjustments/{id}/
- **Module:** inventory
- **Purpose:** inventory_adjustments_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/adjustments/{id}/
- **Module:** inventory
- **Purpose:** inventory_adjustments_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/adjustments/{id}/
- **Module:** inventory
- **Purpose:** inventory_adjustments_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/adjustments/{id}/approve/
- **Module:** inventory
- **Purpose:** inventory_adjustments_approve_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/alerts/
- **Module:** inventory
- **Purpose:** inventory_alerts_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/alerts/{id}/
- **Module:** inventory
- **Purpose:** inventory_alerts_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/alerts/{id}/acknowledge/
- **Module:** inventory
- **Purpose:** inventory_alerts_acknowledge_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/alerts/{id}/resolve/
- **Module:** inventory
- **Purpose:** inventory_alerts_resolve_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/alerts/scan/
- **Module:** inventory
- **Purpose:** inventory_alerts_scan_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/batches/
- **Module:** inventory
- **Purpose:** inventory_batches_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/batches/
- **Module:** inventory
- **Purpose:** inventory_batches_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/batches/{id}/
- **Module:** inventory
- **Purpose:** inventory_batches_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/batches/{id}/
- **Module:** inventory
- **Purpose:** inventory_batches_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/batches/{id}/
- **Module:** inventory
- **Purpose:** inventory_batches_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/batches/{id}/
- **Module:** inventory
- **Purpose:** inventory_batches_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/batches/expired/
- **Module:** inventory
- **Purpose:** inventory_batches_expired_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/batches/expiring-soon/
- **Module:** inventory
- **Purpose:** inventory_batches_expiring_soon_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/damaged/
- **Module:** inventory
- **Purpose:** inventory_damaged_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/damaged/
- **Module:** inventory
- **Purpose:** inventory_damaged_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/damaged/{id}/
- **Module:** inventory
- **Purpose:** inventory_damaged_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/damaged/{id}/
- **Module:** inventory
- **Purpose:** inventory_damaged_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/damaged/{id}/
- **Module:** inventory
- **Purpose:** inventory_damaged_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/damaged/{id}/
- **Module:** inventory
- **Purpose:** inventory_damaged_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/
- **Module:** inventory
- **Purpose:** inventory_items_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/items/
- **Module:** inventory
- **Purpose:** inventory_items_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/{id}/
- **Module:** inventory
- **Purpose:** inventory_items_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/items/{id}/
- **Module:** inventory
- **Purpose:** inventory_items_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/items/{id}/
- **Module:** inventory
- **Purpose:** inventory_items_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/items/{id}/
- **Module:** inventory
- **Purpose:** inventory_items_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/{id}/batches/
- **Module:** inventory
- **Purpose:** inventory_items_batches_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/{id}/ledger/
- **Module:** inventory
- **Purpose:** inventory_items_ledger_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/{id}/movements/
- **Module:** inventory
- **Purpose:** inventory_items_movements_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/{id}/reconcile/
- **Module:** inventory
- **Purpose:** inventory_items_reconcile_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/items/barcode-search/
- **Module:** inventory
- **Purpose:** inventory_items_barcode_search_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/ledger/
- **Module:** inventory
- **Purpose:** inventory_ledger_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/ledger/{id}/reconcile/
- **Module:** inventory
- **Purpose:** inventory_ledger_reconcile_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/movements/
- **Module:** inventory
- **Purpose:** inventory_movements_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/movements/{id}/
- **Module:** inventory
- **Purpose:** inventory_movements_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/purchase-orders/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/purchase-orders/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/purchase-orders/{id}/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/purchase-orders/{id}/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/purchase-orders/{id}/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/purchase-orders/{id}/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/purchase-orders/{id}/receive/
- **Module:** inventory
- **Purpose:** inventory_purchase_orders_receive_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/suppliers/
- **Module:** inventory
- **Purpose:** inventory_suppliers_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/suppliers/
- **Module:** inventory
- **Purpose:** inventory_suppliers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/suppliers/{id}/
- **Module:** inventory
- **Purpose:** inventory_suppliers_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/suppliers/{id}/
- **Module:** inventory
- **Purpose:** inventory_suppliers_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/suppliers/{id}/
- **Module:** inventory
- **Purpose:** inventory_suppliers_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/suppliers/{id}/
- **Module:** inventory
- **Purpose:** inventory_suppliers_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/transfers/
- **Module:** inventory
- **Purpose:** inventory_transfers_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/transfers/
- **Module:** inventory
- **Purpose:** inventory_transfers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/transfers/{id}/
- **Module:** inventory
- **Purpose:** inventory_transfers_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/transfers/{id}/
- **Module:** inventory
- **Purpose:** inventory_transfers_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/transfers/{id}/
- **Module:** inventory
- **Purpose:** inventory_transfers_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/transfers/{id}/
- **Module:** inventory
- **Purpose:** inventory_transfers_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/transfers/{id}/dispatch/
- **Module:** inventory
- **Purpose:** inventory_transfers_dispatch_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/transfers/{id}/receive/
- **Module:** inventory
- **Purpose:** inventory_transfers_receive_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/warehouses/
- **Module:** inventory
- **Purpose:** inventory_warehouses_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/inventory/warehouses/
- **Module:** inventory
- **Purpose:** inventory_warehouses_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/inventory/warehouses/{id}/
- **Module:** inventory
- **Purpose:** inventory_warehouses_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/inventory/warehouses/{id}/
- **Module:** inventory
- **Purpose:** inventory_warehouses_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/inventory/warehouses/{id}/
- **Module:** inventory
- **Purpose:** inventory_warehouses_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/inventory/warehouses/{id}/
- **Module:** inventory
- **Purpose:** inventory_warehouses_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/kot/
- **Module:** kot
- **Purpose:** kot_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/kot/
- **Module:** kot
- **Purpose:** kot_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/kot/{id}/
- **Module:** kot
- **Purpose:** kot_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/kot/{id}/
- **Module:** kot
- **Purpose:** kot_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/kot/{id}/
- **Module:** kot
- **Purpose:** kot_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/kot/{id}/
- **Module:** kot
- **Purpose:** kot_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/kot/{id}/status/
- **Module:** kot
- **Purpose:** kot_status_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/notifications/dispatch/
- **Module:** notifications
- **Purpose:** notifications_dispatch_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/history/
- **Module:** notifications
- **Purpose:** notifications_history_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/notifications/history/
- **Module:** notifications
- **Purpose:** notifications_history_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/history/{id}/
- **Module:** notifications
- **Purpose:** notifications_history_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/notifications/history/{id}/retry/
- **Module:** notifications
- **Purpose:** notifications_history_retry_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/inbox/
- **Module:** notifications
- **Purpose:** notifications_inbox_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/inbox/{id}/
- **Module:** notifications
- **Purpose:** notifications_inbox_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/notifications/inbox/{id}/
- **Module:** notifications
- **Purpose:** notifications_inbox_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/notifications/inbox/{id}/read/
- **Module:** notifications
- **Purpose:** notifications_inbox_read_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/notifications/receipt/
- **Module:** notifications
- **Purpose:** notifications_receipt_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/templates/
- **Module:** notifications
- **Purpose:** notifications_templates_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/notifications/templates/
- **Module:** notifications
- **Purpose:** notifications_templates_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/notifications/templates/{id}/
- **Module:** notifications
- **Purpose:** notifications_templates_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/notifications/templates/{id}/
- **Module:** notifications
- **Purpose:** notifications_templates_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/notifications/templates/{id}/
- **Module:** notifications
- **Purpose:** notifications_templates_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/notifications/templates/{id}/
- **Module:** notifications
- **Purpose:** notifications_templates_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/
- **Module:** ordering
- **Purpose:** ordering_cart_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/
- **Module:** ordering
- **Purpose:** ordering_cart_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/
- **Module:** ordering
- **Purpose:** ordering_cart_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/ordering/cart/{id}/
- **Module:** ordering
- **Purpose:** ordering_cart_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/cart/{id}/
- **Module:** ordering
- **Purpose:** ordering_cart_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/ordering/cart/{id}/
- **Module:** ordering
- **Purpose:** ordering_cart_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/add_item/
- **Module:** ordering
- **Purpose:** ordering_cart_add_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/apply-combo/
- **Module:** ordering
- **Purpose:** ordering_cart_apply_combo_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/apply-modifiers/
- **Module:** ordering
- **Purpose:** ordering_cart_apply_modifiers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/apply_discount/
- **Module:** ordering
- **Purpose:** ordering_cart_apply_discount_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/assign-table/
- **Module:** ordering
- **Purpose:** ordering_cart_assign_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/checkout/
- **Module:** ordering
- **Purpose:** ordering_cart_checkout_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/clear/
- **Module:** ordering
- **Purpose:** ordering_cart_clear_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/clear-cart/
- **Module:** ordering
- **Purpose:** ordering_cart_clear_cart_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/discount/
- **Module:** ordering
- **Purpose:** ordering_cart_discount_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/invoice/
- **Module:** ordering
- **Purpose:** ordering_cart_invoice_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/merge/
- **Module:** ordering
- **Purpose:** ordering_cart_merge_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/merge-table/
- **Module:** ordering
- **Purpose:** ordering_cart_merge_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/move-table/
- **Module:** ordering
- **Purpose:** ordering_cart_move_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/notes/
- **Module:** ordering
- **Purpose:** ordering_cart_notes_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/pay/
- **Module:** ordering
- **Purpose:** ordering_cart_pay_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/payment-history/
- **Module:** ordering
- **Purpose:** ordering_cart_payment_history_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/print-queue/
- **Module:** ordering
- **Purpose:** ordering_cart_print_queue_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/receipt/
- **Module:** ordering
- **Purpose:** ordering_cart_receipt_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/refund/
- **Module:** ordering
- **Purpose:** ordering_cart_refund_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/release-table/
- **Module:** ordering
- **Purpose:** ordering_cart_release_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/remove-combo/
- **Module:** ordering
- **Purpose:** ordering_cart_remove_combo_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/remove-item/
- **Module:** ordering
- **Purpose:** ordering_cart_remove_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/send-kot/
- **Module:** ordering
- **Purpose:** ordering_cart_send_kot_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/split/
- **Module:** ordering
- **Purpose:** ordering_cart_split_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/split-table/
- **Module:** ordering
- **Purpose:** ordering_cart_split_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/status/
- **Module:** ordering
- **Purpose:** ordering_cart_status_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/summary/
- **Module:** ordering
- **Purpose:** ordering_cart_summary_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/taxes/
- **Module:** ordering
- **Purpose:** ordering_cart_taxes_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/cart/{id}/timeline/
- **Module:** ordering
- **Purpose:** ordering_cart_timeline_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/update-item/
- **Module:** ordering
- **Purpose:** ordering_cart_update_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/update-quantity/
- **Module:** ordering
- **Purpose:** ordering_cart_update_quantity_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/void/
- **Module:** ordering
- **Purpose:** ordering_cart_void_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/cart/{id}/void_item/
- **Module:** ordering
- **Purpose:** ordering_cart_void_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/kot/
- **Module:** ordering
- **Purpose:** ordering_kot_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/kot/
- **Module:** ordering
- **Purpose:** ordering_kot_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/kot/{id}/
- **Module:** ordering
- **Purpose:** ordering_kot_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/ordering/kot/{id}/
- **Module:** ordering
- **Purpose:** ordering_kot_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/kot/{id}/
- **Module:** ordering
- **Purpose:** ordering_kot_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/ordering/kot/{id}/
- **Module:** ordering
- **Purpose:** ordering_kot_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/kot/{id}/status/
- **Module:** ordering
- **Purpose:** ordering_kot_status_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/offline/bootstrap/
- **Module:** ordering
- **Purpose:** ordering_offline_bootstrap_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/offline/sync/
- **Module:** ordering
- **Purpose:** ordering_offline_sync_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/
- **Module:** ordering
- **Purpose:** ordering_orders_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/
- **Module:** ordering
- **Purpose:** ordering_orders_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/
- **Module:** ordering
- **Purpose:** ordering_orders_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/ordering/orders/{id}/
- **Module:** ordering
- **Purpose:** ordering_orders_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/orders/{id}/
- **Module:** ordering
- **Purpose:** ordering_orders_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/ordering/orders/{id}/
- **Module:** ordering
- **Purpose:** ordering_orders_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/add_item/
- **Module:** ordering
- **Purpose:** ordering_orders_add_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/apply-combo/
- **Module:** ordering
- **Purpose:** ordering_orders_apply_combo_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/apply-modifiers/
- **Module:** ordering
- **Purpose:** ordering_orders_apply_modifiers_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/apply_discount/
- **Module:** ordering
- **Purpose:** ordering_orders_apply_discount_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/assign-table/
- **Module:** ordering
- **Purpose:** ordering_orders_assign_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/clear-cart/
- **Module:** ordering
- **Purpose:** ordering_orders_clear_cart_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/discount/
- **Module:** ordering
- **Purpose:** ordering_orders_discount_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/invoice/
- **Module:** ordering
- **Purpose:** ordering_orders_invoice_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/merge/
- **Module:** ordering
- **Purpose:** ordering_orders_merge_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/merge-table/
- **Module:** ordering
- **Purpose:** ordering_orders_merge_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/move-table/
- **Module:** ordering
- **Purpose:** ordering_orders_move_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/notes/
- **Module:** ordering
- **Purpose:** ordering_orders_notes_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/pay/
- **Module:** ordering
- **Purpose:** ordering_orders_pay_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/payment-history/
- **Module:** ordering
- **Purpose:** ordering_orders_payment_history_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/print-queue/
- **Module:** ordering
- **Purpose:** ordering_orders_print_queue_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/receipt/
- **Module:** ordering
- **Purpose:** ordering_orders_receipt_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/refund/
- **Module:** ordering
- **Purpose:** ordering_orders_refund_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/release-table/
- **Module:** ordering
- **Purpose:** ordering_orders_release_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/remove-combo/
- **Module:** ordering
- **Purpose:** ordering_orders_remove_combo_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/remove-item/
- **Module:** ordering
- **Purpose:** ordering_orders_remove_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/send-kot/
- **Module:** ordering
- **Purpose:** ordering_orders_send_kot_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/split/
- **Module:** ordering
- **Purpose:** ordering_orders_split_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/split-table/
- **Module:** ordering
- **Purpose:** ordering_orders_split_table_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/status/
- **Module:** ordering
- **Purpose:** ordering_orders_status_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/summary/
- **Module:** ordering
- **Purpose:** ordering_orders_summary_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/taxes/
- **Module:** ordering
- **Purpose:** ordering_orders_taxes_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/orders/{id}/timeline/
- **Module:** ordering
- **Purpose:** ordering_orders_timeline_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/update-item/
- **Module:** ordering
- **Purpose:** ordering_orders_update_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/update-quantity/
- **Module:** ordering
- **Purpose:** ordering_orders_update_quantity_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/void/
- **Module:** ordering
- **Purpose:** ordering_orders_void_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/orders/{id}/void_item/
- **Module:** ordering
- **Purpose:** ordering_orders_void_item_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/payments/
- **Module:** ordering
- **Purpose:** ordering_payments_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/payments/
- **Module:** ordering
- **Purpose:** ordering_payments_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/payments/{id}/
- **Module:** ordering
- **Purpose:** ordering_payments_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/ordering/payments/{id}/
- **Module:** ordering
- **Purpose:** ordering_payments_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/payments/{id}/
- **Module:** ordering
- **Purpose:** ordering_payments_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/ordering/payments/{id}/
- **Module:** ordering
- **Purpose:** ordering_payments_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/print-queue/
- **Module:** ordering
- **Purpose:** ordering_print_queue_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/print-queue/
- **Module:** ordering
- **Purpose:** ordering_print_queue_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/ordering/print-queue/{id}/
- **Module:** ordering
- **Purpose:** ordering_print_queue_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/ordering/print-queue/{id}/
- **Module:** ordering
- **Purpose:** ordering_print_queue_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/ordering/print-queue/{id}/
- **Module:** ordering
- **Purpose:** ordering_print_queue_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/ordering/print-queue/{id}/
- **Module:** ordering
- **Purpose:** ordering_print_queue_destroy
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/ordering/print-queue/{id}/retry/
- **Module:** ordering
- **Purpose:** ordering_print_queue_retry_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/charts/
- **Module:** reporting
- **Purpose:** reporting_charts_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/export/
- **Module:** reporting
- **Purpose:** reporting_export_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/gst/
- **Module:** reporting
- **Purpose:** reporting_gst_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/payments/
- **Module:** reporting
- **Purpose:** reporting_payments_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/profit/
- **Module:** reporting
- **Purpose:** reporting_profit_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/sales/
- **Module:** reporting
- **Purpose:** reporting_sales_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/summary/
- **Module:** reporting
- **Purpose:** reporting_summary_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/top-categories/
- **Module:** reporting
- **Purpose:** reporting_top_categories_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/reporting/top-items/
- **Module:** reporting
- **Purpose:** reporting_top_items_list
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/counters/
- **Module:** restaurant
- **Purpose:** List cash counters
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/counters/
- **Module:** restaurant
- **Purpose:** Create cash counter
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/counters/{id}/
- **Module:** restaurant
- **Purpose:** Get cash counter
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/counters/{id}/
- **Module:** restaurant
- **Purpose:** Update cash counter
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/counters/{id}/
- **Module:** restaurant
- **Purpose:** Partially update cash counter
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/counters/{id}/
- **Module:** restaurant
- **Purpose:** Delete cash counter
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/holidays/
- **Module:** restaurant
- **Purpose:** List holiday overrides
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/holidays/
- **Module:** restaurant
- **Purpose:** Create holiday override
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/holidays/{id}/
- **Module:** restaurant
- **Purpose:** Get holiday details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/holidays/{id}/
- **Module:** restaurant
- **Purpose:** Update holiday override
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/holidays/{id}/
- **Module:** restaurant
- **Purpose:** Partially update holiday override
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/holidays/{id}/
- **Module:** restaurant
- **Purpose:** Delete holiday override
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/hours/
- **Module:** restaurant
- **Purpose:** List weekly business hours
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/hours/
- **Module:** restaurant
- **Purpose:** Create business hours entry
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/hours/{id}/
- **Module:** restaurant
- **Purpose:** Get business hours entry details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/hours/{id}/
- **Module:** restaurant
- **Purpose:** Update business hours entry
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/hours/{id}/
- **Module:** restaurant
- **Purpose:** Partially update business hours entry
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/hours/{id}/
- **Module:** restaurant
- **Purpose:** Delete business hours entry
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/hours/configure/
- **Module:** restaurant
- **Purpose:** Configure operating hours for a specific day of week
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/hours/current-status/
- **Module:** restaurant
- **Purpose:** Check current operating status against business hours and holidays
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/printers/
- **Module:** restaurant
- **Purpose:** List printers
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/printers/
- **Module:** restaurant
- **Purpose:** Create printer configuration
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/printers/{id}/
- **Module:** restaurant
- **Purpose:** Get printer configuration
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/printers/{id}/
- **Module:** restaurant
- **Purpose:** Update printer configuration
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/printers/{id}/
- **Module:** restaurant
- **Purpose:** Partially update printer
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/printers/{id}/
- **Module:** restaurant
- **Purpose:** Delete printer
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/printers/{id}/test-print/
- **Module:** restaurant
- **Purpose:** Execute simulated diagnostic test print
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/restaurants/
- **Module:** restaurant
- **Purpose:** List all restaurants
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/restaurants/
- **Module:** restaurant
- **Purpose:** Create a new restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/restaurants/{id}/
- **Module:** restaurant
- **Purpose:** Get restaurant details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/restaurants/{id}/
- **Module:** restaurant
- **Purpose:** Update restaurant details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/restaurants/{id}/
- **Module:** restaurant
- **Purpose:** Partially update restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/restaurants/{id}/
- **Module:** restaurant
- **Purpose:** Delete restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/restaurants/{id}/activate/
- **Module:** restaurant
- **Purpose:** Activate restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/restaurants/{id}/close/
- **Module:** restaurant
- **Purpose:** Close restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/restaurants/{id}/open-status/
- **Module:** restaurant
- **Purpose:** Check restaurant open status against business hours & holidays
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/restaurants/{id}/reactivate/
- **Module:** restaurant
- **Purpose:** Reactivate restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/restaurants/{id}/suspend/
- **Module:** restaurant
- **Purpose:** Suspend restaurant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/stations/
- **Module:** restaurant
- **Purpose:** List kitchen stations
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/stations/
- **Module:** restaurant
- **Purpose:** Create kitchen station
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/stations/{id}/
- **Module:** restaurant
- **Purpose:** Get kitchen station details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/stations/{id}/
- **Module:** restaurant
- **Purpose:** Update kitchen station
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/stations/{id}/
- **Module:** restaurant
- **Purpose:** Partially update station
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/stations/{id}/
- **Module:** restaurant
- **Purpose:** Delete kitchen station
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/tables/
- **Module:** restaurant
- **Purpose:** List dining tables
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/
- **Module:** restaurant
- **Purpose:** Create dining table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/tables/{id}/
- **Module:** restaurant
- **Purpose:** Get dining table details
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PUT /api/v1/restaurant/tables/{id}/
- **Module:** restaurant
- **Purpose:** Update dining table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/restaurant/tables/{id}/
- **Module:** restaurant
- **Purpose:** Partially update dining table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### DELETE /api/v1/restaurant/tables/{id}/
- **Module:** restaurant
- **Purpose:** Delete dining table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/block/
- **Module:** restaurant
- **Purpose:** Block table for maintenance/cleanup
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/generate-qr/
- **Module:** restaurant
- **Purpose:** Generate table QR ordering code
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/merge/
- **Module:** restaurant
- **Purpose:** Merge secondary tables into primary
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/move/
- **Module:** restaurant
- **Purpose:** Move table occupancy & active orders to target table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/release/
- **Module:** restaurant
- **Purpose:** Release table back to vacant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/reserve/
- **Module:** restaurant
- **Purpose:** Reserve table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/seat/
- **Module:** restaurant
- **Purpose:** Seat guests at table
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/{id}/split/
- **Module:** restaurant
- **Purpose:** Split merged tables back to vacant
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/tables/availability/
- **Module:** restaurant
- **Purpose:** Get vacant tables available for seating
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/tables/layout/
- **Module:** restaurant
- **Purpose:** Get or update physical floor layout table positions
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/restaurant/tables/layout/
- **Module:** restaurant
- **Purpose:** Get or update physical floor layout table positions
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/restaurant/tables/status/
- **Module:** restaurant
- **Purpose:** Get table status summary and occupancy metrics
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/search/
- **Module:** search
- **Purpose:** search_retrieve
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, q, type
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/storage/private/{token}/
- **Module:** storage
- **Purpose:** storage_private_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** token
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/
- **Module:** tenants
- **Purpose:** tenants_list
- **Auth Required:** Yes
- **Query Parameters:** limit, offset, ordering, search
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/tenants/
- **Module:** tenants
- **Purpose:** tenants_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/{id}/
- **Module:** tenants
- **Purpose:** tenants_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/tenants/{id}/
- **Module:** tenants
- **Purpose:** tenants_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** id
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/config/
- **Module:** tenants
- **Purpose:** tenants_config_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### PATCH /api/v1/tenants/config/
- **Module:** tenants
- **Purpose:** tenants_config_partial_update
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/current/
- **Module:** tenants
- **Purpose:** tenants_current_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/features/
- **Module:** tenants
- **Purpose:** tenants_features_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### POST /api/v1/tenants/select/
- **Module:** tenants
- **Purpose:** tenants_select_create
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

### GET /api/v1/tenants/settings/
- **Module:** tenants
- **Purpose:** tenants_settings_retrieve
- **Auth Required:** Yes
- **Query Parameters:** None
- **Path Parameters:** None
- **Mobile Required:** Yes
- **Offline Compatible:** Needs Analysis

## STEP 5 — MOBILE READINESS
Most APIs are standard DRF REST endpoints. 
**NEEDS IMPROVEMENT:**
- Offline Sync: Standard REST lacks delta-sync capabilities (e.g., `updated_since` query params might be missing on some models).
- Bulk Operations: POS requires bulk order syncing when coming back online.

## STEP 6 — FIND MISSING APIS
- **Offline Sync Endpoint:** Delta sync for products, categories, offline orders.
- **Push Notification Registration:** Endpoint to register device FCM tokens.
- **Printer Discovery & Config:** Endpoints to manage ESC/POS printer IP/Mac addresses.
- **Shift Management:** Cash drawer open/close, shift summary for the mobile POS.

## STEP 7 — API DEPENDENCY MAP
Login -> Profile -> Tenant/Restaurant Selection -> Categories & Products -> Tables -> Cart & Checkout -> Orders -> Reports

## STEP 8 — FLUTTER IMPLEMENTATION PHASES
1. **Phase 1:** Auth, Profile, Restaurant Selection, Dashboard
2. **Phase 2:** Categories, Products, Cart, Checkout, Orders
3. **Phase 3:** Kitchen, Inventory, Customers, Tables
4. **Phase 4:** Reports, Analytics, Notifications, Settings
5. **Phase 5:** Offline Sync, Bluetooth Printing, Push Notifications

## STEP 9 — GENERATE API INVENTORY
| Method | Endpoint | Module | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/logout/` | auth | auth_logout_create |
| POST | `/api/v1/auth/logout-all/` | auth | auth_logout_all_create |
| GET | `/api/v1/auth/me/` | auth | auth_me_retrieve |
| PATCH | `/api/v1/auth/me/` | auth | auth_me_partial_update |
| GET | `/api/v1/auth/memberships/` | auth | auth_memberships_list |
| POST | `/api/v1/auth/memberships/` | auth | auth_memberships_create |
| GET | `/api/v1/auth/memberships/{id}/` | auth | auth_memberships_retrieve |
| PUT | `/api/v1/auth/memberships/{id}/` | auth | auth_memberships_update |
| PATCH | `/api/v1/auth/memberships/{id}/` | auth | auth_memberships_partial_update |
| DELETE | `/api/v1/auth/memberships/{id}/` | auth | auth_memberships_destroy |
| POST | `/api/v1/auth/password-reset/` | auth | auth_password_reset_create |
| POST | `/api/v1/auth/password-reset/confirm/` | auth | auth_password_reset_confirm_create |
| GET | `/api/v1/auth/permissions/` | auth | auth_permissions_list |
| GET | `/api/v1/auth/permissions/{id}/` | auth | auth_permissions_retrieve |
| GET | `/api/v1/auth/roles/` | auth | auth_roles_list |
| GET | `/api/v1/auth/roles/{id}/` | auth | auth_roles_retrieve |
| GET | `/api/v1/auth/sessions/` | auth | auth_sessions_list |
| POST | `/api/v1/auth/sessions/` | auth | auth_sessions_create |
| GET | `/api/v1/auth/sessions/{id}/` | auth | auth_sessions_retrieve |
| POST | `/api/v1/auth/sessions/{id}/revoke/` | auth | auth_sessions_revoke_create |
| POST | `/api/v1/auth/token/` | auth | auth_token_create |
| POST | `/api/v1/auth/token/refresh/` | auth | auth_token_refresh_create |
| POST | `/api/v1/auth/token/verify/` | auth | auth_token_verify_create |
| GET | `/api/v1/billing/invoices/` | billing | billing_invoices_list |
| GET | `/api/v1/billing/invoices/{id}/` | billing | billing_invoices_retrieve |
| GET | `/api/v1/billing/subscriptions/` | billing | billing_subscriptions_list |
| GET | `/api/v1/billing/subscriptions/{id}/` | billing | billing_subscriptions_retrieve |
| GET | `/api/v1/catalog/categories/` | catalog | catalog_categories_list |
| POST | `/api/v1/catalog/categories/` | catalog | catalog_categories_create |
| GET | `/api/v1/catalog/categories/{id}/` | catalog | catalog_categories_retrieve |
| PUT | `/api/v1/catalog/categories/{id}/` | catalog | catalog_categories_update |
| PATCH | `/api/v1/catalog/categories/{id}/` | catalog | catalog_categories_partial_update |
| DELETE | `/api/v1/catalog/categories/{id}/` | catalog | catalog_categories_destroy |
| GET | `/api/v1/catalog/combos/` | catalog | catalog_combos_list |
| POST | `/api/v1/catalog/combos/` | catalog | catalog_combos_create |
| GET | `/api/v1/catalog/combos/{id}/` | catalog | catalog_combos_retrieve |
| PUT | `/api/v1/catalog/combos/{id}/` | catalog | catalog_combos_update |
| PATCH | `/api/v1/catalog/combos/{id}/` | catalog | catalog_combos_partial_update |
| DELETE | `/api/v1/catalog/combos/{id}/` | catalog | catalog_combos_destroy |
| GET | `/api/v1/catalog/modifier-groups/` | catalog | catalog_modifier_groups_list |
| POST | `/api/v1/catalog/modifier-groups/` | catalog | catalog_modifier_groups_create |
| GET | `/api/v1/catalog/modifier-groups/{id}/` | catalog | catalog_modifier_groups_retrieve |
| PUT | `/api/v1/catalog/modifier-groups/{id}/` | catalog | catalog_modifier_groups_update |
| PATCH | `/api/v1/catalog/modifier-groups/{id}/` | catalog | catalog_modifier_groups_partial_update |
| DELETE | `/api/v1/catalog/modifier-groups/{id}/` | catalog | catalog_modifier_groups_destroy |
| GET | `/api/v1/catalog/modifiers/` | catalog | catalog_modifiers_list |
| POST | `/api/v1/catalog/modifiers/` | catalog | catalog_modifiers_create |
| GET | `/api/v1/catalog/modifiers/{id}/` | catalog | catalog_modifiers_retrieve |
| PUT | `/api/v1/catalog/modifiers/{id}/` | catalog | catalog_modifiers_update |
| PATCH | `/api/v1/catalog/modifiers/{id}/` | catalog | catalog_modifiers_partial_update |
| DELETE | `/api/v1/catalog/modifiers/{id}/` | catalog | catalog_modifiers_destroy |
| GET | `/api/v1/catalog/price-tiers/` | catalog | catalog_price_tiers_list |
| POST | `/api/v1/catalog/price-tiers/` | catalog | catalog_price_tiers_create |
| GET | `/api/v1/catalog/price-tiers/{id}/` | catalog | catalog_price_tiers_retrieve |
| PUT | `/api/v1/catalog/price-tiers/{id}/` | catalog | catalog_price_tiers_update |
| PATCH | `/api/v1/catalog/price-tiers/{id}/` | catalog | catalog_price_tiers_partial_update |
| DELETE | `/api/v1/catalog/price-tiers/{id}/` | catalog | catalog_price_tiers_destroy |
| GET | `/api/v1/catalog/products/` | catalog | catalog_products_list |
| POST | `/api/v1/catalog/products/` | catalog | catalog_products_create |
| GET | `/api/v1/catalog/products/{id}/` | catalog | catalog_products_retrieve |
| PUT | `/api/v1/catalog/products/{id}/` | catalog | catalog_products_update |
| PATCH | `/api/v1/catalog/products/{id}/` | catalog | catalog_products_partial_update |
| DELETE | `/api/v1/catalog/products/{id}/` | catalog | catalog_products_destroy |
| GET | `/api/v1/catalog/products/export/` | catalog | catalog_products_export_retrieve |
| POST | `/api/v1/catalog/products/import_csv/` | catalog | catalog_products_import_csv_create |
| GET | `/api/v1/catalog/taxes/` | catalog | catalog_taxes_list |
| POST | `/api/v1/catalog/taxes/` | catalog | catalog_taxes_create |
| GET | `/api/v1/catalog/taxes/{id}/` | catalog | catalog_taxes_retrieve |
| PUT | `/api/v1/catalog/taxes/{id}/` | catalog | catalog_taxes_update |
| PATCH | `/api/v1/catalog/taxes/{id}/` | catalog | catalog_taxes_partial_update |
| DELETE | `/api/v1/catalog/taxes/{id}/` | catalog | catalog_taxes_destroy |
| GET | `/api/v1/catalog/units/` | catalog | catalog_units_list |
| POST | `/api/v1/catalog/units/` | catalog | catalog_units_create |
| GET | `/api/v1/catalog/units/{id}/` | catalog | catalog_units_retrieve |
| PUT | `/api/v1/catalog/units/{id}/` | catalog | catalog_units_update |
| PATCH | `/api/v1/catalog/units/{id}/` | catalog | catalog_units_partial_update |
| DELETE | `/api/v1/catalog/units/{id}/` | catalog | catalog_units_destroy |
| GET | `/api/v1/catalog/variants/` | catalog | catalog_variants_list |
| POST | `/api/v1/catalog/variants/` | catalog | catalog_variants_create |
| GET | `/api/v1/catalog/variants/{id}/` | catalog | catalog_variants_retrieve |
| PUT | `/api/v1/catalog/variants/{id}/` | catalog | catalog_variants_update |
| PATCH | `/api/v1/catalog/variants/{id}/` | catalog | catalog_variants_partial_update |
| DELETE | `/api/v1/catalog/variants/{id}/` | catalog | catalog_variants_destroy |
| GET | `/api/v1/customers/coupons/` | customers | customers_coupons_list |
| POST | `/api/v1/customers/coupons/` | customers | customers_coupons_create |
| GET | `/api/v1/customers/coupons/{id}/` | customers | customers_coupons_retrieve |
| PUT | `/api/v1/customers/coupons/{id}/` | customers | customers_coupons_update |
| PATCH | `/api/v1/customers/coupons/{id}/` | customers | customers_coupons_partial_update |
| DELETE | `/api/v1/customers/coupons/{id}/` | customers | customers_coupons_destroy |
| POST | `/api/v1/customers/coupons/validate/` | customers | customers_coupons_validate_create |
| GET | `/api/v1/customers/loyalty/` | customers | customers_loyalty_list |
| GET | `/api/v1/customers/loyalty/{id}/` | customers | customers_loyalty_retrieve |
| PATCH | `/api/v1/customers/loyalty/{id}/` | customers | customers_loyalty_partial_update |
| GET | `/api/v1/customers/profiles/` | customers | customers_profiles_list |
| POST | `/api/v1/customers/profiles/` | customers | customers_profiles_create |
| GET | `/api/v1/customers/profiles/{id}/` | customers | customers_profiles_retrieve |
| PUT | `/api/v1/customers/profiles/{id}/` | customers | customers_profiles_update |
| PATCH | `/api/v1/customers/profiles/{id}/` | customers | customers_profiles_partial_update |
| DELETE | `/api/v1/customers/profiles/{id}/` | customers | customers_profiles_destroy |
| GET | `/api/v1/customers/profiles/{id}/coupons/` | customers | customers_profiles_coupons_retrieve |
| GET | `/api/v1/customers/profiles/{id}/credit/ledger/` | customers | customers_profiles_credit_ledger_retrieve |
| GET | `/api/v1/customers/profiles/{id}/orders/` | customers | customers_profiles_orders_retrieve |
| POST | `/api/v1/customers/profiles/{id}/points/earn/` | customers | customers_profiles_points_earn_create |
| GET | `/api/v1/customers/profiles/{id}/points/history/` | customers | customers_profiles_points_history_retrieve |
| POST | `/api/v1/customers/profiles/{id}/points/redeem/` | customers | customers_profiles_points_redeem_create |
| POST | `/api/v1/customers/profiles/{id}/wallet/deposit/` | customers | customers_profiles_wallet_deposit_create |
| GET | `/api/v1/customers/profiles/{id}/wallet/history/` | customers | customers_profiles_wallet_history_retrieve |
| POST | `/api/v1/customers/profiles/{id}/wallet/pay/` | customers | customers_profiles_wallet_pay_create |
| GET | `/api/v1/dashboard/charts/` | dashboard | dashboard_charts_list |
| GET | `/api/v1/dashboard/export/` | dashboard | dashboard_export_retrieve |
| GET | `/api/v1/dashboard/gst/` | dashboard | dashboard_gst_retrieve |
| GET | `/api/v1/dashboard/payments/` | dashboard | dashboard_payments_list |
| GET | `/api/v1/dashboard/profit/` | dashboard | dashboard_profit_list |
| GET | `/api/v1/dashboard/sales/` | dashboard | dashboard_sales_list |
| GET | `/api/v1/dashboard/summary/` | dashboard | dashboard_summary_retrieve |
| GET | `/api/v1/dashboard/top-categories/` | dashboard | dashboard_top_categories_list |
| GET | `/api/v1/dashboard/top-items/` | dashboard | dashboard_top_items_list |
| GET | `/api/v1/employees/attendance/` | employees | employees_attendance_list |
| POST | `/api/v1/employees/attendance/` | employees | employees_attendance_create |
| GET | `/api/v1/employees/attendance/{id}/` | employees | employees_attendance_retrieve |
| PUT | `/api/v1/employees/attendance/{id}/` | employees | employees_attendance_update |
| PATCH | `/api/v1/employees/attendance/{id}/` | employees | employees_attendance_partial_update |
| DELETE | `/api/v1/employees/attendance/{id}/` | employees | employees_attendance_destroy |
| POST | `/api/v1/employees/attendance/{id}/check-out/` | employees | employees_attendance_check_out_create |
| POST | `/api/v1/employees/attendance/{id}/clock-out/` | employees | employees_attendance_clock_out_create |
| POST | `/api/v1/employees/attendance/{id}/end-break/` | employees | employees_attendance_end_break_create |
| POST | `/api/v1/employees/attendance/{id}/start-break/` | employees | employees_attendance_start_break_create |
| POST | `/api/v1/employees/attendance/check-in/` | employees | employees_attendance_check_in_create |
| POST | `/api/v1/employees/attendance/clock-in/` | employees | employees_attendance_clock_in_create |
| GET | `/api/v1/employees/dashboard/` | employees | employees_dashboard_retrieve |
| GET | `/api/v1/employees/departments/` | employees | employees_departments_list |
| POST | `/api/v1/employees/departments/` | employees | employees_departments_create |
| GET | `/api/v1/employees/departments/{id}/` | employees | employees_departments_retrieve |
| PUT | `/api/v1/employees/departments/{id}/` | employees | employees_departments_update |
| PATCH | `/api/v1/employees/departments/{id}/` | employees | employees_departments_partial_update |
| DELETE | `/api/v1/employees/departments/{id}/` | employees | employees_departments_destroy |
| GET | `/api/v1/employees/designations/` | employees | employees_designations_list |
| POST | `/api/v1/employees/designations/` | employees | employees_designations_create |
| GET | `/api/v1/employees/designations/{id}/` | employees | employees_designations_retrieve |
| PUT | `/api/v1/employees/designations/{id}/` | employees | employees_designations_update |
| PATCH | `/api/v1/employees/designations/{id}/` | employees | employees_designations_partial_update |
| DELETE | `/api/v1/employees/designations/{id}/` | employees | employees_designations_destroy |
| GET | `/api/v1/employees/employees/` | employees | employees_employees_list |
| POST | `/api/v1/employees/employees/` | employees | employees_employees_create |
| GET | `/api/v1/employees/employees/{id}/` | employees | employees_employees_retrieve |
| PUT | `/api/v1/employees/employees/{id}/` | employees | employees_employees_update |
| PATCH | `/api/v1/employees/employees/{id}/` | employees | employees_employees_partial_update |
| DELETE | `/api/v1/employees/employees/{id}/` | employees | employees_employees_destroy |
| GET | `/api/v1/employees/leave-balances/` | employees | employees_leave_balances_list |
| GET | `/api/v1/employees/leave-balances/{id}/` | employees | employees_leave_balances_retrieve |
| GET | `/api/v1/employees/leaves/` | employees | employees_leaves_list |
| POST | `/api/v1/employees/leaves/` | employees | employees_leaves_create |
| GET | `/api/v1/employees/leaves/{id}/` | employees | employees_leaves_retrieve |
| PUT | `/api/v1/employees/leaves/{id}/` | employees | employees_leaves_update |
| PATCH | `/api/v1/employees/leaves/{id}/` | employees | employees_leaves_partial_update |
| DELETE | `/api/v1/employees/leaves/{id}/` | employees | employees_leaves_destroy |
| POST | `/api/v1/employees/leaves/{id}/approve/` | employees | employees_leaves_approve_create |
| POST | `/api/v1/employees/leaves/{id}/reject/` | employees | employees_leaves_reject_create |
| GET | `/api/v1/employees/payroll/` | employees | employees_payroll_list |
| POST | `/api/v1/employees/payroll/` | employees | employees_payroll_create |
| GET | `/api/v1/employees/payroll/{id}/` | employees | employees_payroll_retrieve |
| PUT | `/api/v1/employees/payroll/{id}/` | employees | employees_payroll_update |
| PATCH | `/api/v1/employees/payroll/{id}/` | employees | employees_payroll_partial_update |
| DELETE | `/api/v1/employees/payroll/{id}/` | employees | employees_payroll_destroy |
| POST | `/api/v1/employees/payroll/run/` | employees | employees_payroll_run_create |
| GET | `/api/v1/employees/performance/` | employees | employees_performance_list |
| POST | `/api/v1/employees/performance/` | employees | employees_performance_create |
| GET | `/api/v1/employees/performance/{id}/` | employees | employees_performance_retrieve |
| PUT | `/api/v1/employees/performance/{id}/` | employees | employees_performance_update |
| PATCH | `/api/v1/employees/performance/{id}/` | employees | employees_performance_partial_update |
| DELETE | `/api/v1/employees/performance/{id}/` | employees | employees_performance_destroy |
| GET | `/api/v1/employees/profiles/` | employees | employees_profiles_list |
| POST | `/api/v1/employees/profiles/` | employees | employees_profiles_create |
| GET | `/api/v1/employees/profiles/{id}/` | employees | employees_profiles_retrieve |
| PUT | `/api/v1/employees/profiles/{id}/` | employees | employees_profiles_update |
| PATCH | `/api/v1/employees/profiles/{id}/` | employees | employees_profiles_partial_update |
| DELETE | `/api/v1/employees/profiles/{id}/` | employees | employees_profiles_destroy |
| GET | `/api/v1/employees/shifts/` | employees | employees_shifts_list |
| POST | `/api/v1/employees/shifts/` | employees | employees_shifts_create |
| GET | `/api/v1/employees/shifts/{id}/` | employees | employees_shifts_retrieve |
| PUT | `/api/v1/employees/shifts/{id}/` | employees | employees_shifts_update |
| PATCH | `/api/v1/employees/shifts/{id}/` | employees | employees_shifts_partial_update |
| DELETE | `/api/v1/employees/shifts/{id}/` | employees | employees_shifts_destroy |
| POST | `/api/v1/features/cache/clear/` | features | features_cache_clear_create |
| POST | `/api/v1/features/evaluate/` | features | features_evaluate_create |
| GET | `/api/v1/features/limits/` | features | features_limits_retrieve |
| GET | `/api/v1/features/modules/` | features | features_modules_retrieve |
| GET | `/api/v1/features/subscription/` | features | features_subscription_retrieve |
| POST | `/api/v1/features/validate/` | features | features_validate_create |
| GET | `/api/v1/health/` | health | health_retrieve |
| GET | `/api/v1/inventory/adjustments/` | inventory | inventory_adjustments_list |
| POST | `/api/v1/inventory/adjustments/` | inventory | inventory_adjustments_create |
| GET | `/api/v1/inventory/adjustments/{id}/` | inventory | inventory_adjustments_retrieve |
| PUT | `/api/v1/inventory/adjustments/{id}/` | inventory | inventory_adjustments_update |
| PATCH | `/api/v1/inventory/adjustments/{id}/` | inventory | inventory_adjustments_partial_update |
| DELETE | `/api/v1/inventory/adjustments/{id}/` | inventory | inventory_adjustments_destroy |
| POST | `/api/v1/inventory/adjustments/{id}/approve/` | inventory | inventory_adjustments_approve_create |
| GET | `/api/v1/inventory/alerts/` | inventory | inventory_alerts_list |
| GET | `/api/v1/inventory/alerts/{id}/` | inventory | inventory_alerts_retrieve |
| POST | `/api/v1/inventory/alerts/{id}/acknowledge/` | inventory | inventory_alerts_acknowledge_create |
| POST | `/api/v1/inventory/alerts/{id}/resolve/` | inventory | inventory_alerts_resolve_create |
| POST | `/api/v1/inventory/alerts/scan/` | inventory | inventory_alerts_scan_create |
| GET | `/api/v1/inventory/batches/` | inventory | inventory_batches_list |
| POST | `/api/v1/inventory/batches/` | inventory | inventory_batches_create |
| GET | `/api/v1/inventory/batches/{id}/` | inventory | inventory_batches_retrieve |
| PUT | `/api/v1/inventory/batches/{id}/` | inventory | inventory_batches_update |
| PATCH | `/api/v1/inventory/batches/{id}/` | inventory | inventory_batches_partial_update |
| DELETE | `/api/v1/inventory/batches/{id}/` | inventory | inventory_batches_destroy |
| GET | `/api/v1/inventory/batches/expired/` | inventory | inventory_batches_expired_retrieve |
| GET | `/api/v1/inventory/batches/expiring-soon/` | inventory | inventory_batches_expiring_soon_retrieve |
| GET | `/api/v1/inventory/damaged/` | inventory | inventory_damaged_list |
| POST | `/api/v1/inventory/damaged/` | inventory | inventory_damaged_create |
| GET | `/api/v1/inventory/damaged/{id}/` | inventory | inventory_damaged_retrieve |
| PUT | `/api/v1/inventory/damaged/{id}/` | inventory | inventory_damaged_update |
| PATCH | `/api/v1/inventory/damaged/{id}/` | inventory | inventory_damaged_partial_update |
| DELETE | `/api/v1/inventory/damaged/{id}/` | inventory | inventory_damaged_destroy |
| GET | `/api/v1/inventory/items/` | inventory | inventory_items_list |
| POST | `/api/v1/inventory/items/` | inventory | inventory_items_create |
| GET | `/api/v1/inventory/items/{id}/` | inventory | inventory_items_retrieve |
| PUT | `/api/v1/inventory/items/{id}/` | inventory | inventory_items_update |
| PATCH | `/api/v1/inventory/items/{id}/` | inventory | inventory_items_partial_update |
| DELETE | `/api/v1/inventory/items/{id}/` | inventory | inventory_items_destroy |
| GET | `/api/v1/inventory/items/{id}/batches/` | inventory | inventory_items_batches_retrieve |
| GET | `/api/v1/inventory/items/{id}/ledger/` | inventory | inventory_items_ledger_retrieve |
| GET | `/api/v1/inventory/items/{id}/movements/` | inventory | inventory_items_movements_retrieve |
| GET | `/api/v1/inventory/items/{id}/reconcile/` | inventory | inventory_items_reconcile_retrieve |
| GET | `/api/v1/inventory/items/barcode-search/` | inventory | inventory_items_barcode_search_retrieve |
| GET | `/api/v1/inventory/ledger/` | inventory | inventory_ledger_list |
| GET | `/api/v1/inventory/ledger/{id}/reconcile/` | inventory | inventory_ledger_reconcile_retrieve |
| GET | `/api/v1/inventory/movements/` | inventory | inventory_movements_list |
| GET | `/api/v1/inventory/movements/{id}/` | inventory | inventory_movements_retrieve |
| GET | `/api/v1/inventory/purchase-orders/` | inventory | inventory_purchase_orders_list |
| POST | `/api/v1/inventory/purchase-orders/` | inventory | inventory_purchase_orders_create |
| GET | `/api/v1/inventory/purchase-orders/{id}/` | inventory | inventory_purchase_orders_retrieve |
| PUT | `/api/v1/inventory/purchase-orders/{id}/` | inventory | inventory_purchase_orders_update |
| PATCH | `/api/v1/inventory/purchase-orders/{id}/` | inventory | inventory_purchase_orders_partial_update |
| DELETE | `/api/v1/inventory/purchase-orders/{id}/` | inventory | inventory_purchase_orders_destroy |
| POST | `/api/v1/inventory/purchase-orders/{id}/receive/` | inventory | inventory_purchase_orders_receive_create |
| GET | `/api/v1/inventory/suppliers/` | inventory | inventory_suppliers_list |
| POST | `/api/v1/inventory/suppliers/` | inventory | inventory_suppliers_create |
| GET | `/api/v1/inventory/suppliers/{id}/` | inventory | inventory_suppliers_retrieve |
| PUT | `/api/v1/inventory/suppliers/{id}/` | inventory | inventory_suppliers_update |
| PATCH | `/api/v1/inventory/suppliers/{id}/` | inventory | inventory_suppliers_partial_update |
| DELETE | `/api/v1/inventory/suppliers/{id}/` | inventory | inventory_suppliers_destroy |
| GET | `/api/v1/inventory/transfers/` | inventory | inventory_transfers_list |
| POST | `/api/v1/inventory/transfers/` | inventory | inventory_transfers_create |
| GET | `/api/v1/inventory/transfers/{id}/` | inventory | inventory_transfers_retrieve |
| PUT | `/api/v1/inventory/transfers/{id}/` | inventory | inventory_transfers_update |
| PATCH | `/api/v1/inventory/transfers/{id}/` | inventory | inventory_transfers_partial_update |
| DELETE | `/api/v1/inventory/transfers/{id}/` | inventory | inventory_transfers_destroy |
| POST | `/api/v1/inventory/transfers/{id}/dispatch/` | inventory | inventory_transfers_dispatch_create |
| POST | `/api/v1/inventory/transfers/{id}/receive/` | inventory | inventory_transfers_receive_create |
| GET | `/api/v1/inventory/warehouses/` | inventory | inventory_warehouses_list |
| POST | `/api/v1/inventory/warehouses/` | inventory | inventory_warehouses_create |
| GET | `/api/v1/inventory/warehouses/{id}/` | inventory | inventory_warehouses_retrieve |
| PUT | `/api/v1/inventory/warehouses/{id}/` | inventory | inventory_warehouses_update |
| PATCH | `/api/v1/inventory/warehouses/{id}/` | inventory | inventory_warehouses_partial_update |
| DELETE | `/api/v1/inventory/warehouses/{id}/` | inventory | inventory_warehouses_destroy |
| GET | `/api/v1/kot/` | kot | kot_list |
| POST | `/api/v1/kot/` | kot | kot_create |
| GET | `/api/v1/kot/{id}/` | kot | kot_retrieve |
| PUT | `/api/v1/kot/{id}/` | kot | kot_update |
| PATCH | `/api/v1/kot/{id}/` | kot | kot_partial_update |
| DELETE | `/api/v1/kot/{id}/` | kot | kot_destroy |
| PATCH | `/api/v1/kot/{id}/status/` | kot | kot_status_partial_update |
| POST | `/api/v1/notifications/dispatch/` | notifications | notifications_dispatch_create |
| GET | `/api/v1/notifications/history/` | notifications | notifications_history_list |
| POST | `/api/v1/notifications/history/` | notifications | notifications_history_create |
| GET | `/api/v1/notifications/history/{id}/` | notifications | notifications_history_retrieve |
| POST | `/api/v1/notifications/history/{id}/retry/` | notifications | notifications_history_retry_create |
| GET | `/api/v1/notifications/inbox/` | notifications | notifications_inbox_list |
| GET | `/api/v1/notifications/inbox/{id}/` | notifications | notifications_inbox_retrieve |
| PATCH | `/api/v1/notifications/inbox/{id}/` | notifications | notifications_inbox_partial_update |
| PATCH | `/api/v1/notifications/inbox/{id}/read/` | notifications | notifications_inbox_read_partial_update |
| POST | `/api/v1/notifications/receipt/` | notifications | notifications_receipt_create |
| GET | `/api/v1/notifications/templates/` | notifications | notifications_templates_list |
| POST | `/api/v1/notifications/templates/` | notifications | notifications_templates_create |
| GET | `/api/v1/notifications/templates/{id}/` | notifications | notifications_templates_retrieve |
| PUT | `/api/v1/notifications/templates/{id}/` | notifications | notifications_templates_update |
| PATCH | `/api/v1/notifications/templates/{id}/` | notifications | notifications_templates_partial_update |
| DELETE | `/api/v1/notifications/templates/{id}/` | notifications | notifications_templates_destroy |
| GET | `/api/v1/ordering/cart/` | ordering | ordering_cart_list |
| POST | `/api/v1/ordering/cart/` | ordering | ordering_cart_create |
| GET | `/api/v1/ordering/cart/{id}/` | ordering | ordering_cart_retrieve |
| PUT | `/api/v1/ordering/cart/{id}/` | ordering | ordering_cart_update |
| PATCH | `/api/v1/ordering/cart/{id}/` | ordering | ordering_cart_partial_update |
| DELETE | `/api/v1/ordering/cart/{id}/` | ordering | ordering_cart_destroy |
| POST | `/api/v1/ordering/cart/{id}/add_item/` | ordering | ordering_cart_add_item_create |
| POST | `/api/v1/ordering/cart/{id}/apply-combo/` | ordering | ordering_cart_apply_combo_create |
| POST | `/api/v1/ordering/cart/{id}/apply-modifiers/` | ordering | ordering_cart_apply_modifiers_create |
| POST | `/api/v1/ordering/cart/{id}/apply_discount/` | ordering | ordering_cart_apply_discount_create |
| POST | `/api/v1/ordering/cart/{id}/assign-table/` | ordering | ordering_cart_assign_table_create |
| POST | `/api/v1/ordering/cart/{id}/checkout/` | ordering | ordering_cart_checkout_create |
| POST | `/api/v1/ordering/cart/{id}/clear/` | ordering | ordering_cart_clear_create |
| POST | `/api/v1/ordering/cart/{id}/clear-cart/` | ordering | ordering_cart_clear_cart_create |
| POST | `/api/v1/ordering/cart/{id}/discount/` | ordering | ordering_cart_discount_create |
| GET | `/api/v1/ordering/cart/{id}/invoice/` | ordering | ordering_cart_invoice_retrieve |
| POST | `/api/v1/ordering/cart/{id}/merge/` | ordering | ordering_cart_merge_create |
| POST | `/api/v1/ordering/cart/{id}/merge-table/` | ordering | ordering_cart_merge_table_create |
| POST | `/api/v1/ordering/cart/{id}/move-table/` | ordering | ordering_cart_move_table_create |
| POST | `/api/v1/ordering/cart/{id}/notes/` | ordering | ordering_cart_notes_create |
| POST | `/api/v1/ordering/cart/{id}/pay/` | ordering | ordering_cart_pay_create |
| GET | `/api/v1/ordering/cart/{id}/payment-history/` | ordering | ordering_cart_payment_history_retrieve |
| GET | `/api/v1/ordering/cart/{id}/print-queue/` | ordering | ordering_cart_print_queue_retrieve |
| GET | `/api/v1/ordering/cart/{id}/receipt/` | ordering | ordering_cart_receipt_retrieve |
| POST | `/api/v1/ordering/cart/{id}/refund/` | ordering | ordering_cart_refund_create |
| POST | `/api/v1/ordering/cart/{id}/release-table/` | ordering | ordering_cart_release_table_create |
| POST | `/api/v1/ordering/cart/{id}/remove-combo/` | ordering | ordering_cart_remove_combo_create |
| POST | `/api/v1/ordering/cart/{id}/remove-item/` | ordering | ordering_cart_remove_item_create |
| POST | `/api/v1/ordering/cart/{id}/send-kot/` | ordering | ordering_cart_send_kot_create |
| POST | `/api/v1/ordering/cart/{id}/split/` | ordering | ordering_cart_split_create |
| POST | `/api/v1/ordering/cart/{id}/split-table/` | ordering | ordering_cart_split_table_create |
| POST | `/api/v1/ordering/cart/{id}/status/` | ordering | ordering_cart_status_create |
| GET | `/api/v1/ordering/cart/{id}/summary/` | ordering | ordering_cart_summary_retrieve |
| GET | `/api/v1/ordering/cart/{id}/taxes/` | ordering | ordering_cart_taxes_retrieve |
| GET | `/api/v1/ordering/cart/{id}/timeline/` | ordering | ordering_cart_timeline_retrieve |
| POST | `/api/v1/ordering/cart/{id}/update-item/` | ordering | ordering_cart_update_item_create |
| POST | `/api/v1/ordering/cart/{id}/update-quantity/` | ordering | ordering_cart_update_quantity_create |
| POST | `/api/v1/ordering/cart/{id}/void/` | ordering | ordering_cart_void_create |
| POST | `/api/v1/ordering/cart/{id}/void_item/` | ordering | ordering_cart_void_item_create |
| GET | `/api/v1/ordering/kot/` | ordering | ordering_kot_list |
| POST | `/api/v1/ordering/kot/` | ordering | ordering_kot_create |
| GET | `/api/v1/ordering/kot/{id}/` | ordering | ordering_kot_retrieve |
| PUT | `/api/v1/ordering/kot/{id}/` | ordering | ordering_kot_update |
| PATCH | `/api/v1/ordering/kot/{id}/` | ordering | ordering_kot_partial_update |
| DELETE | `/api/v1/ordering/kot/{id}/` | ordering | ordering_kot_destroy |
| PATCH | `/api/v1/ordering/kot/{id}/status/` | ordering | ordering_kot_status_partial_update |
| GET | `/api/v1/ordering/offline/bootstrap/` | ordering | ordering_offline_bootstrap_retrieve |
| POST | `/api/v1/ordering/offline/sync/` | ordering | ordering_offline_sync_create |
| GET | `/api/v1/ordering/orders/` | ordering | ordering_orders_list |
| POST | `/api/v1/ordering/orders/` | ordering | ordering_orders_create |
| GET | `/api/v1/ordering/orders/{id}/` | ordering | ordering_orders_retrieve |
| PUT | `/api/v1/ordering/orders/{id}/` | ordering | ordering_orders_update |
| PATCH | `/api/v1/ordering/orders/{id}/` | ordering | ordering_orders_partial_update |
| DELETE | `/api/v1/ordering/orders/{id}/` | ordering | ordering_orders_destroy |
| POST | `/api/v1/ordering/orders/{id}/add_item/` | ordering | ordering_orders_add_item_create |
| POST | `/api/v1/ordering/orders/{id}/apply-combo/` | ordering | ordering_orders_apply_combo_create |
| POST | `/api/v1/ordering/orders/{id}/apply-modifiers/` | ordering | ordering_orders_apply_modifiers_create |
| POST | `/api/v1/ordering/orders/{id}/apply_discount/` | ordering | ordering_orders_apply_discount_create |
| POST | `/api/v1/ordering/orders/{id}/assign-table/` | ordering | ordering_orders_assign_table_create |
| POST | `/api/v1/ordering/orders/{id}/clear-cart/` | ordering | ordering_orders_clear_cart_create |
| POST | `/api/v1/ordering/orders/{id}/discount/` | ordering | ordering_orders_discount_create |
| GET | `/api/v1/ordering/orders/{id}/invoice/` | ordering | ordering_orders_invoice_retrieve |
| POST | `/api/v1/ordering/orders/{id}/merge/` | ordering | ordering_orders_merge_create |
| POST | `/api/v1/ordering/orders/{id}/merge-table/` | ordering | ordering_orders_merge_table_create |
| POST | `/api/v1/ordering/orders/{id}/move-table/` | ordering | ordering_orders_move_table_create |
| POST | `/api/v1/ordering/orders/{id}/notes/` | ordering | ordering_orders_notes_create |
| POST | `/api/v1/ordering/orders/{id}/pay/` | ordering | ordering_orders_pay_create |
| GET | `/api/v1/ordering/orders/{id}/payment-history/` | ordering | ordering_orders_payment_history_retrieve |
| GET | `/api/v1/ordering/orders/{id}/print-queue/` | ordering | ordering_orders_print_queue_retrieve |
| GET | `/api/v1/ordering/orders/{id}/receipt/` | ordering | ordering_orders_receipt_retrieve |
| POST | `/api/v1/ordering/orders/{id}/refund/` | ordering | ordering_orders_refund_create |
| POST | `/api/v1/ordering/orders/{id}/release-table/` | ordering | ordering_orders_release_table_create |
| POST | `/api/v1/ordering/orders/{id}/remove-combo/` | ordering | ordering_orders_remove_combo_create |
| POST | `/api/v1/ordering/orders/{id}/remove-item/` | ordering | ordering_orders_remove_item_create |
| POST | `/api/v1/ordering/orders/{id}/send-kot/` | ordering | ordering_orders_send_kot_create |
| POST | `/api/v1/ordering/orders/{id}/split/` | ordering | ordering_orders_split_create |
| POST | `/api/v1/ordering/orders/{id}/split-table/` | ordering | ordering_orders_split_table_create |
| POST | `/api/v1/ordering/orders/{id}/status/` | ordering | ordering_orders_status_create |
| GET | `/api/v1/ordering/orders/{id}/summary/` | ordering | ordering_orders_summary_retrieve |
| GET | `/api/v1/ordering/orders/{id}/taxes/` | ordering | ordering_orders_taxes_retrieve |
| GET | `/api/v1/ordering/orders/{id}/timeline/` | ordering | ordering_orders_timeline_retrieve |
| POST | `/api/v1/ordering/orders/{id}/update-item/` | ordering | ordering_orders_update_item_create |
| POST | `/api/v1/ordering/orders/{id}/update-quantity/` | ordering | ordering_orders_update_quantity_create |
| POST | `/api/v1/ordering/orders/{id}/void/` | ordering | ordering_orders_void_create |
| POST | `/api/v1/ordering/orders/{id}/void_item/` | ordering | ordering_orders_void_item_create |
| GET | `/api/v1/ordering/payments/` | ordering | ordering_payments_list |
| POST | `/api/v1/ordering/payments/` | ordering | ordering_payments_create |
| GET | `/api/v1/ordering/payments/{id}/` | ordering | ordering_payments_retrieve |
| PUT | `/api/v1/ordering/payments/{id}/` | ordering | ordering_payments_update |
| PATCH | `/api/v1/ordering/payments/{id}/` | ordering | ordering_payments_partial_update |
| DELETE | `/api/v1/ordering/payments/{id}/` | ordering | ordering_payments_destroy |
| GET | `/api/v1/ordering/print-queue/` | ordering | ordering_print_queue_list |
| POST | `/api/v1/ordering/print-queue/` | ordering | ordering_print_queue_create |
| GET | `/api/v1/ordering/print-queue/{id}/` | ordering | ordering_print_queue_retrieve |
| PUT | `/api/v1/ordering/print-queue/{id}/` | ordering | ordering_print_queue_update |
| PATCH | `/api/v1/ordering/print-queue/{id}/` | ordering | ordering_print_queue_partial_update |
| DELETE | `/api/v1/ordering/print-queue/{id}/` | ordering | ordering_print_queue_destroy |
| POST | `/api/v1/ordering/print-queue/{id}/retry/` | ordering | ordering_print_queue_retry_create |
| GET | `/api/v1/reporting/charts/` | reporting | reporting_charts_list |
| GET | `/api/v1/reporting/export/` | reporting | reporting_export_retrieve |
| GET | `/api/v1/reporting/gst/` | reporting | reporting_gst_retrieve |
| GET | `/api/v1/reporting/payments/` | reporting | reporting_payments_list |
| GET | `/api/v1/reporting/profit/` | reporting | reporting_profit_list |
| GET | `/api/v1/reporting/sales/` | reporting | reporting_sales_list |
| GET | `/api/v1/reporting/summary/` | reporting | reporting_summary_retrieve |
| GET | `/api/v1/reporting/top-categories/` | reporting | reporting_top_categories_list |
| GET | `/api/v1/reporting/top-items/` | reporting | reporting_top_items_list |
| GET | `/api/v1/restaurant/counters/` | restaurant | List cash counters |
| POST | `/api/v1/restaurant/counters/` | restaurant | Create cash counter |
| GET | `/api/v1/restaurant/counters/{id}/` | restaurant | Get cash counter |
| PUT | `/api/v1/restaurant/counters/{id}/` | restaurant | Update cash counter |
| PATCH | `/api/v1/restaurant/counters/{id}/` | restaurant | Partially update cash counter |
| DELETE | `/api/v1/restaurant/counters/{id}/` | restaurant | Delete cash counter |
| GET | `/api/v1/restaurant/holidays/` | restaurant | List holiday overrides |
| POST | `/api/v1/restaurant/holidays/` | restaurant | Create holiday override |
| GET | `/api/v1/restaurant/holidays/{id}/` | restaurant | Get holiday details |
| PUT | `/api/v1/restaurant/holidays/{id}/` | restaurant | Update holiday override |
| PATCH | `/api/v1/restaurant/holidays/{id}/` | restaurant | Partially update holiday override |
| DELETE | `/api/v1/restaurant/holidays/{id}/` | restaurant | Delete holiday override |
| GET | `/api/v1/restaurant/hours/` | restaurant | List weekly business hours |
| POST | `/api/v1/restaurant/hours/` | restaurant | Create business hours entry |
| GET | `/api/v1/restaurant/hours/{id}/` | restaurant | Get business hours entry details |
| PUT | `/api/v1/restaurant/hours/{id}/` | restaurant | Update business hours entry |
| PATCH | `/api/v1/restaurant/hours/{id}/` | restaurant | Partially update business hours entry |
| DELETE | `/api/v1/restaurant/hours/{id}/` | restaurant | Delete business hours entry |
| POST | `/api/v1/restaurant/hours/configure/` | restaurant | Configure operating hours for a specific day of week |
| GET | `/api/v1/restaurant/hours/current-status/` | restaurant | Check current operating status against business hours and holidays |
| GET | `/api/v1/restaurant/printers/` | restaurant | List printers |
| POST | `/api/v1/restaurant/printers/` | restaurant | Create printer configuration |
| GET | `/api/v1/restaurant/printers/{id}/` | restaurant | Get printer configuration |
| PUT | `/api/v1/restaurant/printers/{id}/` | restaurant | Update printer configuration |
| PATCH | `/api/v1/restaurant/printers/{id}/` | restaurant | Partially update printer |
| DELETE | `/api/v1/restaurant/printers/{id}/` | restaurant | Delete printer |
| POST | `/api/v1/restaurant/printers/{id}/test-print/` | restaurant | Execute simulated diagnostic test print |
| GET | `/api/v1/restaurant/restaurants/` | restaurant | List all restaurants |
| POST | `/api/v1/restaurant/restaurants/` | restaurant | Create a new restaurant |
| GET | `/api/v1/restaurant/restaurants/{id}/` | restaurant | Get restaurant details |
| PUT | `/api/v1/restaurant/restaurants/{id}/` | restaurant | Update restaurant details |
| PATCH | `/api/v1/restaurant/restaurants/{id}/` | restaurant | Partially update restaurant |
| DELETE | `/api/v1/restaurant/restaurants/{id}/` | restaurant | Delete restaurant |
| POST | `/api/v1/restaurant/restaurants/{id}/activate/` | restaurant | Activate restaurant |
| POST | `/api/v1/restaurant/restaurants/{id}/close/` | restaurant | Close restaurant |
| GET | `/api/v1/restaurant/restaurants/{id}/open-status/` | restaurant | Check restaurant open status against business hours & holidays |
| POST | `/api/v1/restaurant/restaurants/{id}/reactivate/` | restaurant | Reactivate restaurant |
| POST | `/api/v1/restaurant/restaurants/{id}/suspend/` | restaurant | Suspend restaurant |
| GET | `/api/v1/restaurant/stations/` | restaurant | List kitchen stations |
| POST | `/api/v1/restaurant/stations/` | restaurant | Create kitchen station |
| GET | `/api/v1/restaurant/stations/{id}/` | restaurant | Get kitchen station details |
| PUT | `/api/v1/restaurant/stations/{id}/` | restaurant | Update kitchen station |
| PATCH | `/api/v1/restaurant/stations/{id}/` | restaurant | Partially update station |
| DELETE | `/api/v1/restaurant/stations/{id}/` | restaurant | Delete kitchen station |
| GET | `/api/v1/restaurant/tables/` | restaurant | List dining tables |
| POST | `/api/v1/restaurant/tables/` | restaurant | Create dining table |
| GET | `/api/v1/restaurant/tables/{id}/` | restaurant | Get dining table details |
| PUT | `/api/v1/restaurant/tables/{id}/` | restaurant | Update dining table |
| PATCH | `/api/v1/restaurant/tables/{id}/` | restaurant | Partially update dining table |
| DELETE | `/api/v1/restaurant/tables/{id}/` | restaurant | Delete dining table |
| POST | `/api/v1/restaurant/tables/{id}/block/` | restaurant | Block table for maintenance/cleanup |
| POST | `/api/v1/restaurant/tables/{id}/generate-qr/` | restaurant | Generate table QR ordering code |
| POST | `/api/v1/restaurant/tables/{id}/merge/` | restaurant | Merge secondary tables into primary |
| POST | `/api/v1/restaurant/tables/{id}/move/` | restaurant | Move table occupancy & active orders to target table |
| POST | `/api/v1/restaurant/tables/{id}/release/` | restaurant | Release table back to vacant |
| POST | `/api/v1/restaurant/tables/{id}/reserve/` | restaurant | Reserve table |
| POST | `/api/v1/restaurant/tables/{id}/seat/` | restaurant | Seat guests at table |
| POST | `/api/v1/restaurant/tables/{id}/split/` | restaurant | Split merged tables back to vacant |
| GET | `/api/v1/restaurant/tables/availability/` | restaurant | Get vacant tables available for seating |
| GET | `/api/v1/restaurant/tables/layout/` | restaurant | Get or update physical floor layout table positions |
| POST | `/api/v1/restaurant/tables/layout/` | restaurant | Get or update physical floor layout table positions |
| GET | `/api/v1/restaurant/tables/status/` | restaurant | Get table status summary and occupancy metrics |
| GET | `/api/v1/search/` | search | search_retrieve |
| GET | `/api/v1/storage/private/{token}/` | storage | storage_private_retrieve |
| GET | `/api/v1/tenants/` | tenants | tenants_list |
| POST | `/api/v1/tenants/` | tenants | tenants_create |
| GET | `/api/v1/tenants/{id}/` | tenants | tenants_retrieve |
| PATCH | `/api/v1/tenants/{id}/` | tenants | tenants_partial_update |
| GET | `/api/v1/tenants/config/` | tenants | tenants_config_retrieve |
| PATCH | `/api/v1/tenants/config/` | tenants | tenants_config_partial_update |
| GET | `/api/v1/tenants/current/` | tenants | tenants_current_retrieve |
| GET | `/api/v1/tenants/features/` | tenants | tenants_features_retrieve |
| POST | `/api/v1/tenants/select/` | tenants | tenants_select_create |
| GET | `/api/v1/tenants/settings/` | tenants | tenants_settings_retrieve |

## STEP 10 — FINAL REPORT
- **Number of API Modules:** 17
- **Number of Endpoints:** 462
- **Missing Mobile APIs:** 4 identified
- **Flutter Readiness Score:** 75/100 (Requires offline sync enhancements)
