/**
 * Nextora POS Enterprise Offline Synchronization Engine (sync.js)
 * Implements Phase 7 (Sync Engine), Phase 8 (Conflict Resolution), and Phase 9 (Connectivity Monitoring)
 */

(function (global) {
  'use strict';

  const SYNC_ENDPOINT = '/api/v1/ordering/offline/sync/';
  const BOOTSTRAP_ENDPOINT = '/api/v1/ordering/offline/bootstrap/';

  const NextoraOfflineSync = {
    isSyncing: false,
    syncIntervalId: null,

    /**
     * Initialize event listeners for online/offline events & periodic sync
     */
    init() {
      global.addEventListener('online', () => {
        this.updateStatusBadge('Online');
        this.triggerSync();
      });

      global.addEventListener('offline', () => {
        this.updateStatusBadge('Offline Mode');
      });

      // Listen for Service Worker background sync messages
      if (navigator.serviceWorker) {
        navigator.serviceWorker.addEventListener('message', (event) => {
          if (event.data && event.data.type === 'SYNC_TRIGGERED') {
            this.triggerSync();
          }
        });
      }

      // Initial badge state setup
      this.updateStatusBadge(navigator.onLine ? 'Online' : 'Offline Mode');

      // Periodic check every 30 seconds when online
      this.syncIntervalId = setInterval(() => {
        if (navigator.onLine) {
          this.triggerSync();
        }
      }, 30000);
    },

    /**
     * Update header connectivity status indicator
     */
    updateStatusBadge(statusText) {
      const pill = document.querySelector('.top-rail__status-pill');
      if (!pill) return;

      pill.className = 'top-rail__status-pill';
      let dotColorClass = 'bg-semantic-success';

      switch (statusText) {
        case 'Online':
        case 'Sync Completed':
          pill.classList.add('top-rail__status-pill--ok');
          break;
        case 'Offline Mode':
          pill.classList.add('top-rail__status-pill--warn');
          dotColorClass = 'bg-semantic-warning';
          break;
        case 'Synchronizing...':
          pill.classList.add('top-rail__status-pill--info');
          dotColorClass = 'bg-brand-default animate-pulse';
          break;
        case 'Sync Failed':
          pill.classList.add('top-rail__status-pill--err');
          dotColorClass = 'bg-semantic-danger';
          break;
      }

      pill.innerHTML = `<span class="status-rail__dot ${dotColorClass}" aria-hidden="true"></span>${statusText}`;
      
      // Dispatch global events for toast notifications
      if (statusText === 'Sync Completed') {
        window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'success', message: 'Offline changes synced successfully.' } }));
      } else if (statusText === 'Sync Failed') {
        window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'error', message: 'Failed to sync offline changes. Will retry.' } }));
      } else if (statusText === 'Offline Mode') {
        window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'warning', message: 'You are offline. Changes are saved locally.' } }));
      }
    },

    /**
     * Pull complete snapshot from backend to prime Dexie IndexedDB
     */
    async bootstrapCatalog() {
      if (!navigator.onLine || !global.NextoraOfflineDB) return;
      try {
        const response = await fetch(BOOTSTRAP_ENDPOINT, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });
        if (!response.ok) return;

        const data = await response.json();
        const db = global.NextoraOfflineDB;

        if (data.products && data.products.length) {
          await db.products.bulkPut(data.products);
        }
        if (data.categories && data.categories.length) {
          await db.categories.bulkPut(data.categories);
        }
        if (data.taxes && data.taxes.length) {
          await db.taxes.bulkPut(data.taxes);
        }
        if (data.user_permissions) {
          await global.NextoraOfflineAuth?.storeSession(data.user_permissions);
        }
        await db.sync_metadata.put({ key: 'catalog', last_synced_at: Date.now(), version: data.version || 1 });
        console.log('[OfflineSync] Master catalog snapshot successfully cached.');
      } catch (err) {
        console.warn('[OfflineSync] Catalog bootstrap request failed:', err);
      }
    },

    /**
     * Enqueue an offline mutation to IndexedDB sync_queue
     */
    async enqueueMutation(actionType, payload) {
      if (!global.NextoraOfflineDB) return null;
      const idempotencyKey = 'IDEM-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
      const queueItem = {
        idempotency_key: idempotencyKey,
        action_type: actionType,
        payload: payload,
        status: 'pending',
        created_at: Date.now(),
        retry_count: 0
      };
      await global.NextoraOfflineDB.sync_queue.put(queueItem);

      // Attempt immediate sync if online
      if (navigator.onLine) {
        this.triggerSync();
      } else {
        this.updateStatusBadge('Offline Mode');
      }
      return idempotencyKey;
    },

    /**
     * Process pending queue against authoritative server API
     */
    async triggerSync() {
      if (this.isSyncing || !navigator.onLine || !global.NextoraOfflineDB) return;

      const pendingItems = await global.NextoraOfflineDB.sync_queue
        .filter(item => item.status === 'pending')
        .toArray();

      if (!pendingItems || pendingItems.length === 0) {
        return;
      }

      this.isSyncing = true;
      this.updateStatusBadge('Synchronizing...');

      // Sort ordered queue by created_at ascending
      pendingItems.sort((a, b) => a.created_at - b.created_at);

      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

      try {
        const response = await fetch(SYNC_ENDPOINT, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            transactions: pendingItems
          })
        });

        if (response.ok) {
          const resultData = await response.json();
          // Remove or mark synced items
          for (const item of pendingItems) {
            await global.NextoraOfflineDB.sync_queue.put({
              ...item,
              status: 'synced',
              synced_at: Date.now()
            });
          }
          this.updateStatusBadge('Sync Completed');
          // Re-bootstrap catalog after sync to ensure updated inventory levels
          await this.bootstrapCatalog();
        } else if (response.status === 401 || response.status === 403) {
          console.warn('[OfflineSync] Session expired on server. Forcing re-authentication.');
          this.updateStatusBadge('Authentication Required');
          if (global.NextoraOfflineAuth) {
            await global.NextoraOfflineAuth.clearSession();
          }
          window.dispatchEvent(new CustomEvent('notify', { detail: { type: 'error', message: 'Session expired. Please log in again to sync pending bills.' } }));
          setTimeout(() => {
            window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
          }, 2000);
        } else {
          // Increment retry_count with exponential backoff capping
          for (const item of pendingItems) {
            await global.NextoraOfflineDB.sync_queue.put({
              ...item,
              retry_count: (item.retry_count || 0) + 1
            });
          }
          this.updateStatusBadge('Sync Failed');
        }
      } catch (err) {
        console.warn('[OfflineSync] Error executing batch sync:', err);
        this.updateStatusBadge('Sync Failed');
      } finally {
        this.isSyncing = false;
      }
    }
  };

  global.NextoraOfflineSync = NextoraOfflineSync;
  global.addEventListener('DOMContentLoaded', () => {
    NextoraOfflineSync.init();
  });
})(typeof window !== 'undefined' ? window : this);
