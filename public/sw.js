/* Kalolsavam PWA Service Worker */
const CACHE_NAME = 'kal-__SW_BUILD__';

const PRECACHE_FLEET = [
  './',
  'venues/',
  'venues-live/',
  'venues-location/',
  'venues-find/',
  'facilities/',
  'transportation/',
  'help/'
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
        keys.filter(function (k) { return k !== CACHE_NAME; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

function cachePut(req, res) {
  if (res && res.ok && !res.redirected && res.type === 'basic') {
    var copy = res.clone();
    caches.open(CACHE_NAME).then(function (c) { c.put(req, copy); });
  }
}

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  if (
    url.origin !== location.origin ||
    url.pathname.indexOf('/api/') >= 0 ||
    url.pathname.indexOf('/admin') >= 0 ||
    url.pathname.indexOf('/stagemaster') >= 0 ||
    url.pathname.startsWith('/dashboard')
  ) {
    return;
  }

  // Cache-first for hashed Astro assets and static images/SVGs
  if (
    url.pathname.indexOf('/astro/') >= 0 ||
    url.pathname.indexOf('/assets/img/') >= 0 ||
    url.pathname.indexOf('/assets/svg/') >= 0
  ) {
    event.respondWith(
      caches.match(event.request).then(function (hit) {
        if (hit) return hit;
        return fetch(event.request).then(function (res) {
          cachePut(event.request, res);
          return res;
        });
      })
    );
    return;
  }

  // Network-first for HTML navigations and unhashed JS
  event.respondWith(
    fetch(event.request).then(function (networkRes) {
      cachePut(event.request, networkRes);
      return networkRes;
    }).catch(function () {
      return caches.match(event.request).then(function (cached) {
        if (cached) return cached;
        if (event.request.mode === 'navigate') return caches.match('./');
        return undefined;
      });
    })
  );
});
