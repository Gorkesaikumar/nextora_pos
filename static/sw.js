/**
 * Nextora POS Enterprise Service Worker (sw.js)
 * Supports 72-Hour Offline-First POS Operation & Background Sync
 */

const CACHE_VERSION = 'nextora-pos-v2.1-20260724';
const CORE_STATIC_CACHE = `static-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;
const OFFLINE_FALLBACK_URL = '/offline/';

// Application shell assets required for offline rendering
const CORE_ASSETS = [
  '/',
  '/pos/',
  '/offline/',
  '/static/css/tailwind.css',
  '/static/css/main.css',
  '/static/css/tokens.css',
  '/static/manifest.json',
  '/static/js/vendor/dexie.min.js',
  '/static/js/offline/db.js',
  '/static/js/offline/auth.js',
  '/static/js/offline/sync.js',
  '/static/js/offline/pos-offline.js',
  '/offline/', // Offline fallback page
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CORE_STATIC_CACHE).then((cache) => {
      // Precache core assets silently; do not fail install if one asset is still building
      return cache.addAll(CORE_ASSETS).catch((err) => {
        console.warn('[SW] Non-fatal precache warning:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CORE_STATIC_CACHE && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] Purging legacy cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Network-first for dynamic pages/APIs, Cache-first for static assets
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Never intercept non-GET requests (POST/PUT/DELETE are handled by offline sync engine)
  if (request.method !== 'GET') {
    return;
  }

  // Exempt WebSocket, Auth, and specific sensitive API routes from SW interception
  if (url.pathname.startsWith('/ws/') || url.pathname.includes('/auth/logout') || url.pathname.includes('/api/sensitive/')) {
    return;
  }

  // Static Assets: Cache-first strategy
  if (url.pathname.startsWith('/static/') || url.hostname !== self.location.hostname) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseToCache = networkResponse.clone();
            caches.open(CORE_STATIC_CACHE).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return networkResponse;
        }).catch(() => {
          // Return fallback empty or cached response
          return caches.match(request);
        });
      })
    );
    return;
  }

  // HTML Pages & API Read Endpoints: Network-first with runtime fallback
  event.respondWith(
    fetch(request).then((networkResponse) => {
      // Cache successful HTML pages for offline navigation
      if (networkResponse && networkResponse.status === 200 && request.headers.get('accept')?.includes('text/html')) {
        const responseToCache = networkResponse.clone();
        caches.open(RUNTIME_CACHE).then((cache) => {
          cache.put(request, responseToCache);
        });
      }
      return networkResponse;
    }).catch(async () => {
      // Network failed -> return cached version if available
      const cachedResponse = await caches.match(request);
      if (cachedResponse) {
        return cachedResponse;
      }
      // If HTML navigation fails offline, serve the cached POS shell, dashboard, or offline fallback
      if (request.headers.get('accept')?.includes('text/html')) {
        return caches.match('/pos/') || caches.match('/') || caches.match(OFFLINE_FALLBACK_URL);
      }
      return new Response(JSON.stringify({ detail: 'Offline mode active. This resource is not cached.' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
      });
    })
  );
});

// Service Worker messaging interface
self.addEventListener('message', (event) => {
  if (!event.data) return;
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'CLEAR_CACHES') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
    );
  }

  if (event.data.type === 'CLEAR_TENANT_CACHES') {
    event.waitUntil(
      caches.delete(RUNTIME_CACHE)
    );
  }
});

// Background Sync API integration
self.addEventListener('sync', (event) => {
  if (event.tag === 'nextora-offline-sync') {
    event.waitUntil(
      self.clients.matchAll({ includeUncontrolled: true, type: 'window' }).then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'SYNC_TRIGGERED' });
        });
      })
    );
  }
});
