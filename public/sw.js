/* Kalolsavam PWA Service Worker — v4.1.0 */
const CACHE_NAME = 'kal-v19';
const PAGE_CACHE_NAME = 'kal-page-cache-v11';

const PRECACHE_FLEET = [
  './',
  'venues',
  'venues-live',
  'venues-location',
  'venues-find',
  'facilities',
  'facilities-green-room',
  'facilities-toilet',
  'transportation',
  'transportation-bus',
  'transportation-auto',
  'results',
  'results-offstage',
  'results-individual',
  'results-group',
  'media',
  'developers',
  'help'
];

self.addEventListener('install', function (event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return Promise.all(
        PRECACHE_FLEET.map(function (url) {
          return cache.add(url).catch(function () {});
        })
      );
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME && k !== PAGE_CACHE_NAME; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Never intercept API endpoints, SSE streams, or Admin/Staff portals
  if (
    url.origin !== location.origin ||
    url.pathname.indexOf('/api/') >= 0 ||
    url.pathname.indexOf('/admin') >= 0 ||
    url.pathname.indexOf('/stagemaster') >= 0 ||
    url.pathname.indexOf('/dashboard') >= 0
  ) {
    return;
  }

  // Network-first for JavaScript files so code updates take effect immediately
  if (url.pathname.endsWith('.js')) {
    event.respondWith(
      fetch(event.request).then(function (res) {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(function (c) { c.put(event.request, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Cache-first for images and media
  if (url.pathname.indexOf('/assets/img/') >= 0 || url.pathname.indexOf('/assets/svg/') >= 0) {
    event.respondWith(
      caches.match(event.request).then(function (hit) {
        if (hit) return hit;
        return fetch(event.request).then(function (res) {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then(function (c) { c.put(event.request, copy); });
          }
          return res;
        });
      })
    );
    return;
  }

  // Navigation requests: Network-first with cache fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then(function (networkRes) {
        if (networkRes.ok) {
          const copy = networkRes.clone();
          caches.open(PAGE_CACHE_NAME).then(function (c) { c.put(event.request, copy); });
        }
        return networkRes;
      }).catch(function () {
        return caches.match(event.request).then(function (cached) {
          return cached || caches.match('./') || caches.match('index.html');
        });
      })
    );
    return;
  }

  // Stale-While-Revalidate for other GET requests
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      const fetchPromise = fetch(event.request).then(function (networkRes) {
        if (networkRes.ok) {
          const copy = networkRes.clone();
          caches.open(PAGE_CACHE_NAME).then(function (c) { c.put(event.request, copy); });
        }
        return networkRes;
      }).catch(function () {
        return cached;
      });

      return cached || fetchPromise;
    })
  );
});
