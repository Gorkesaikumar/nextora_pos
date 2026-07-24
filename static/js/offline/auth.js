/**
 * Nextora POS Enterprise Offline Authentication Manager (auth.js)
 * Implements Phase 10: 72-Hour Offline Operation Grace Period & RBAC verification
 */

(function (global) {
  'use strict';

  const MAX_OFFLINE_DURATION_MS = 72 * 60 * 60 * 1000; // 72 Hours in Milliseconds
  const AUTH_STORE_KEY = 'current_user_session';

  const NextoraOfflineAuth = {
    /**
     * Store active session & user profile in IDB upon successful online login / bootstrap
     */
    async storeSession(userSession) {
      if (!global.NextoraOfflineDB) return;
      const payload = {
        id: userSession.id || userSession.user_id,
        user_id: userSession.id || userSession.user_id,
        tenant_id: userSession.tenant_id,
        email: userSession.email,
        name: userSession.name || userSession.email,
        roles: userSession.roles || [],
        permissions: userSession.permissions || [],
        cached_at: Date.now(),
        expires_at: Date.now() + MAX_OFFLINE_DURATION_MS
      };
      await global.NextoraOfflineDB.user_permissions.put(payload);
      return payload;
    },

    /**
     * Retrieve the cached session if within the 72-hour grace period
     */
    async getActiveOfflineSession() {
      if (!global.NextoraOfflineDB) return null;
      const sessions = await global.NextoraOfflineDB.user_permissions.toArray();
      if (!sessions || sessions.length === 0) return null;

      // Find most recently cached session
      const session = sessions.sort((a, b) => (b.cached_at || 0) - (a.cached_at || 0))[0];
      const now = Date.now();

      // Check 72-hour grace period expiration
      if (now > session.expires_at) {
        console.warn('[OfflineAuth] 72-Hour Offline Grace Period expired. Online re-authentication required.');
        return {
          expired: true,
          reason: 'OFFLINE_GRACE_PERIOD_EXPIRED',
          session: null
        };
      }

      return {
        expired: false,
        session: session
      };
    },

    /**
     * Check if offline user has specific RBAC permission
     */
    async hasPermission(permissionCode) {
      const authState = await this.getActiveOfflineSession();
      if (!authState || authState.expired || !authState.session) {
        return false;
      }
      const permissions = authState.session.permissions || [];
      return permissions.includes(permissionCode) || permissions.includes('*') || authState.session.roles?.includes('super_admin');
    },

    /**
     * Clear cached offline session upon explicit logout
     */
    async clearSession() {
      if (!global.NextoraOfflineDB) return;
      
      console.warn('[OfflineAuth] Executing aggressive tenant data purge.');

      // 1. Wipe all IndexedDB Tables (destroying the sync queue, catalog, and auth)
      await Promise.all([
        global.NextoraOfflineDB.user_permissions.clear(),
        global.NextoraOfflineDB.products.clear(),
        global.NextoraOfflineDB.categories.clear(),
        global.NextoraOfflineDB.inventory.clear(),
        global.NextoraOfflineDB.customers.clear(),
        global.NextoraOfflineDB.suppliers.clear(),
        global.NextoraOfflineDB.sales.clear(),
        global.NextoraOfflineDB.orders.clear(),
        global.NextoraOfflineDB.cart.clear(),
        global.NextoraOfflineDB.payments.clear(),
        global.NextoraOfflineDB.receipts.clear(),
        global.NextoraOfflineDB.discounts.clear(),
        global.NextoraOfflineDB.taxes.clear(),
        global.NextoraOfflineDB.branch_config.clear(),
        global.NextoraOfflineDB.company_settings.clear(),
        global.NextoraOfflineDB.printer_config.clear(),
        global.NextoraOfflineDB.sync_metadata.clear(),
        global.NextoraOfflineDB.sync_queue.clear(),
        global.NextoraOfflineDB.audit_log.clear()
      ]);

      // 2. Wipe Local and Session Storage
      localStorage.clear();
      sessionStorage.clear();

      // 3. Command Service Worker to drop HTML/API caches but keep the App Shell
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_TENANT_CACHES' });
      }
    }
  };

  global.NextoraOfflineAuth = NextoraOfflineAuth;

  // 4. Intercept explicit logout links to purge data before navigating away
  global.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && link.href && link.href.includes('logout')) {
      e.preventDefault();
      NextoraOfflineAuth.clearSession().finally(() => {
        window.location.href = link.href;
      });
    }
  });

})(typeof window !== 'undefined' ? window : this);
