/**
 * Nextora POS Enterprise Offline Database (db.js)
 * IndexedDB schema powered by Dexie.js for Phase 3 Offline Architecture
 */

(function (global) {
  'use strict';

  if (!global.Dexie) {
    console.error('[OfflineDB] Dexie is not loaded.');
    return;
  }

  const db = new Dexie('NextoraOfflineDB');

  // Enterprise schema covering all required offline POS stores
  db.version(1).stores({
    products: 'id, tenant_id, category_id, sku, barcode, name, is_active',
    categories: 'id, tenant_id, parent_id, sort_order',
    inventory: 'id, tenant_id, product_id, branch_id, qty_available',
    customers: 'id, tenant_id, phone, name, email',
    suppliers: 'id, tenant_id, name',
    sales: 'id, tenant_id, offline_invoice_no, status, created_at',
    orders: 'id, tenant_id, offline_reference_id, status, created_at',
    cart: 'id, tenant_id, updated_at',
    payments: 'id, order_id, method, amount',
    receipts: 'id, order_id',
    discounts: 'id, tenant_id, code, is_active',
    taxes: 'id, tenant_id, name, rate',
    branch_config: 'id, tenant_id',
    company_settings: 'id, tenant_id',
    user_permissions: 'id, user_id, tenant_id',
    printer_config: 'id, tenant_id, name',
    sync_queue: '++id, idempotency_key, action_type, status, created_at, retry_count',
    audit_log: '++id, tenant_id, actor_id, action, timestamp',
    sync_metadata: 'key, last_synced_at, version'
  });

  db.open().then(() => {
    console.log('[OfflineDB] NextoraOfflineDB successfully initialized.');
  }).catch((err) => {
    console.error('[OfflineDB] Failed to open NextoraOfflineDB:', err);
  });

  global.NextoraOfflineDB = db;
})(typeof window !== 'undefined' ? window : this);
