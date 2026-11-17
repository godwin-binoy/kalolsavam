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
  'venues-stage/10/',
  'venues-stage/11/',
  'venues-stage/12/',
  'venues-stage/13/',
  'venues-stage/14/',
  'venues-stage/15/',
  'venues-stage/16/',
  'venues-stage/17/',
  'venues-stage/18/',
  'venues-stage/19/',
  'venues-stage/20/',
  'venues-stage/21/',
  'venues-stage/22/',
  'venues-stage/23/',
  'venues-stage/24/',
  'venues-stage/25/',
  'venues-stage/26/',
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
  'help/',
  'assets/css/tokens.css',
  'assets/js/common.js',
  'assets/js/lang.js',
  'assets/img/logo.webp',
  'assets/img/master-logo.webp',
  'manifest.json'
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

function isHtmlPath(pathname) {
  var last = pathname.split('/').pop() || '';
  return last.indexOf('.') < 0;
}

function cachePut(req, res) {
  if (!res || !res.ok || res.type !== 'basic') return;
  var ct = res.headers.get('content-type') || '';
  var u = new URL(req.url);

  var cleanPromise = res.redirected
    ? res.clone().arrayBuffer().then(function (buf) {
        return new Response(buf, { status: res.status, statusText: res.statusText, headers: res.headers });
      })
    : Promise.resolve(res.clone());

  cleanPromise.then(function (clean) {
    caches.open(CACHE_NAME).then(function (c) {
      c.put(req, clean.clone());
      if (ct.indexOf('text/html') >= 0 && isHtmlPath(u.pathname) && u.pathname !== '/') {
        var altPath = u.pathname.endsWith('/') ? u.pathname.slice(0, -1) : u.pathname + '/';
        var altUrl = u.origin + altPath + u.search;
        c.put(new Request(altUrl), clean.clone());
      }
    });
  }).catch(function () {});
}

function matchCached(req) {
  return caches.match(req).then(function (hit) {
    if (hit) return hit;
    var u = new URL(req.url);
    if (!isHtmlPath(u.pathname) || u.pathname === '/') return undefined;
    var altPath = u.pathname.endsWith('/') ? u.pathname.slice(0, -1) : u.pathname + '/';
    return caches.match(u.origin + altPath + u.search);
  });
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

  if (url.pathname.endsWith('/config.js')) {
    event.respondWith(
      fetch(new Request(event.request, { cache: 'no-cache' }))
        .then(function (res) { cachePut(event.request, res); return res; })
        .catch(function () { return caches.match(event.request); })
    );
    return;
  }

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

  // Stale-While-Revalidate for all pages and app JS: 0ms switch + background refresh
  event.respondWith(
    matchCached(event.request).then(function (cached) {
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
