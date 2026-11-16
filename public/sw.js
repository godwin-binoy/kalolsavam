/* Kalolsavam PWA Service Worker — stamped per build */
const CACHE_NAME = 'kal-__SW_BUILD__';

const PRECACHE_FLEET = [
  './',
  'venues/',
  'venues-live/',
  'venues-location/',
  'venues-find/',
  'venues-stage/1/',
  'venues-stage/2/',
  'venues-stage/3/',
  'venues-stage/4/',
  'venues-stage/5/',
  'venues-stage/6/',
  'venues-stage/7/',
  'venues-stage/8/',
  'venues-stage/9/',
  'facilities/',
  'facilities-green-room/',
  'facilities-toilet/',
  'facilities-water/',
  'facilities-dining/',
  'media/',
  'live-stream/',
  'transportation/',
  'transportation-bus/',
  'transportation-auto/',
  'developers/',
  'help/'
];

self.addEventListener('install', function (event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return Promise.all(
        PRECACHE_FLEET.map(function (url) {
          return cache.add(new Request(url, { cache: 'reload' })).catch(function () {});
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
    }).then(function () {
      return self.clients.claim();
    }).then(function () {
      return self.clients.matchAll({ type: 'window' }).then(function (clients) {
        clients.forEach(function (client) {
          client.postMessage({ type: 'KAL_SW_UPDATED', version: CACHE_NAME });
        });
      });
    })
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

  var url = new URL(event.request.url);
  if (
    url.origin !== location.origin ||
    url.pathname.indexOf('/api/') >= 0 ||
    url.pathname.indexOf('/admin') >= 0 ||
    url.pathname.indexOf('/stagemaster') >= 0 ||
    url.pathname.indexOf('/dataworker') >= 0 ||
    url.pathname.startsWith('/dashboard')
  ) {
    return;
  }

  // Config is always network-first so API origin updates apply immediately
  if (url.pathname.endsWith('/config.js')) {
    event.respondWith(
      fetch(new Request(event.request, { cache: 'no-cache' }))
        .then(function (res) { cachePut(event.request, res); return res; })
        .catch(function () { return caches.match(event.request); })
    );
    return;
  }

  // Cache-first for hashed/static assets
  if (
    url.pathname.indexOf('/astro/') >= 0 ||
    url.pathname.indexOf('/assets/img/') >= 0 ||
    url.pathname.indexOf('/assets/svg/') >= 0 ||
    url.pathname.indexOf('/assets/css/') >= 0
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

  // Stale-While-Revalidate for HTML pages and app JS: instant switch + fresh background sync
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      var networkFetch = fetch(new Request(event.request, { cache: 'no-cache' }))
        .then(function (networkRes) {
          cachePut(event.request, networkRes);
          return networkRes;
        })
        .catch(function () {
          return cached || (event.request.mode === 'navigate' ? caches.match('./') : undefined);
        });

      if (cached) {
        event.waitUntil(networkFetch);
        return cached;
      }
      return networkFetch;
    })
  );
});
