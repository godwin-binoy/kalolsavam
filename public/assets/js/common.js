/* Global Kalolsavam core: API/DOM helpers, mobile frosted drawer, utility dock scroll, SW & prefetch. */
(function () {
  'use strict';
  window.KalApp = { onCleanup: function () {} };

  var BASE = (function () {
    var b = document.body && document.body.getAttribute('data-api');
    if (b === 'same-origin' || b === '') return '';
    if (b != null) return b.replace(/\/+$/, '');
    if (typeof window.KAL_API_BASE === 'string' && window.KAL_API_BASE) {
      return window.KAL_API_BASE === 'same-origin' ? '' : window.KAL_API_BASE.replace(/\/+$/, '');
    }
    var m = document.querySelector('meta[name="kal-api"]');
    if (m && m.content) return m.content === 'same-origin' ? '' : m.content.replace(/\/+$/, '');
    if (location.port === '8000' || location.hostname === 'testserver' || location.hostname === 'apikalolsavammala.dpdns.org') return '';
    return 'https://apikalolsavammala.dpdns.org';
  })();

  function url(p) { return (!p || /^https?:\/\//i.test(p)) ? p : BASE + (p.charAt(0) === '/' ? p : '/' + p); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(id) { return document.getElementById(id); }
  function on(root, evt, sel, fn) {
    if (!root) return;
    root.addEventListener(evt, function (e) {
      var target = e.target && e.target.closest ? e.target.closest(sel) : null;
      if (target && root.contains(target)) fn(target, e);
    });
  }
  function debounce(fn, ms) {
    var t = null;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms || 200);
    };
  }
  async function fetchJSON(path, opts) {
    var r = await fetch(url(path), Object.assign({ credentials: 'omit' }, opts || {}));
    var data = await r.json().catch(function () { return {}; });
    if (!r.ok) throw { status: r.status, data: data };
    return data;
  }
  function normName(s) { return String(s || '').toLowerCase().replace(/^stage\s*\d+\s*[-—:.]?\s*/i, '').trim(); }
  function matchStage(venue, slug, name) {
    if (!venue) return false;
    if (slug && venue.slug && String(venue.slug).toLowerCase() === String(slug).toLowerCase()) return true;
    return normName(venue.name) === normName(name);
  }
  function poll(fn, ms) {
    var timer = null, stopped = false;
    function tick() { if (!stopped && !document.hidden) fn(); }
    function start() { if (!stopped && !timer) timer = setInterval(tick, ms); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function onVis() { if (document.hidden) stop(); else { tick(); start(); } }
    fn();
    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVis);
    return function () { stopped = true; stop(); document.removeEventListener('visibilitychange', onVis); };
  }

  window.Kal = {
    apiBase: function () { return BASE; },
    url: url, esc: esc, el: el, on: on, debounce: debounce,
    fetchJSON: fetchJSON, normName: normName, matchStage: matchStage, poll: poll
  };

  // Public-site shell behavior (skipped on staff portals)
  if (document.body && !document.body.dataset.portal) {
    var html = document.documentElement, themeBtn = el('theme'), menu = el('menu'),
        mnav = el('mnav'), header = document.querySelector('.hdr'), dock = document.querySelector('.utility-dock');

    // Resilient theme toggle using event delegation on document
    document.addEventListener('click', function (ev) {
      var btn = ev.target && ev.target.closest ? ev.target.closest('#theme') : null;
      if (btn) {
        ev.preventDefault();
        var isDark = document.documentElement.classList.toggle('dark');
        try { localStorage.setItem('kal_theme', isDark ? 'dark' : 'light'); } catch (e) {}
      }
    }, true);

    if (menu && mnav) {
      function closeDrawer() {
        if (header) header.classList.remove('open');
        mnav.classList.remove('open');
        menu.setAttribute('aria-expanded', 'false');
        if (dock && window.pageYOffset <= 60) dock.classList.remove('dock-hidden');
      }
      function openDrawer() {
        if (header) {
          var h = Math.ceil(mnav.getBoundingClientRect().height);
          if (h > 0) header.style.setProperty('--drawer-h', (h + 1) + 'px');
          header.classList.add('open');
        }
        if (dock) dock.classList.add('dock-hidden');
        mnav.classList.add('open');
        menu.setAttribute('aria-expanded', 'true');
      }
      menu.addEventListener('click', function () { mnav.classList.contains('open') ? closeDrawer() : openDrawer(); });
      mnav.addEventListener('click', function (ev) { if (ev.target.closest('a')) closeDrawer(); });
      document.addEventListener('click', function (ev) {
        if (mnav.classList.contains('open') && !mnav.contains(ev.target) && !menu.contains(ev.target)) closeDrawer();
      }, true);
      document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && mnav.classList.contains('open')) closeDrawer(); });
    }

    if (dock) {
      var lastY = window.pageYOffset || document.documentElement.scrollTop || 0;
      window.addEventListener('scroll', function () {
        if (mnav && mnav.classList.contains('open')) return;
        var y = window.pageYOffset || document.documentElement.scrollTop || 0;
        if (y <= 40) { dock.classList.remove('dock-hidden'); lastY = y; return; }
        if (Math.abs(y - lastY) < 6) return;
        dock.classList.toggle('dock-hidden', y > lastY && y > 60);
        lastY = y;
      }, { passive: true });
    }

    var prefetched = new Set();
    function canPrefetch(href) {
      if (!href || prefetched.size >= 45) return null;
      try {
        var u = new URL(href, location.origin);
        if (u.origin !== location.origin || (u.pathname === location.pathname && !u.search)) return null;
        if (/^\/(admin|stagemaster|dataworker|dashboard|api)\b/.test(u.pathname)) return null;
        if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(u.pathname)) return null;
        return prefetched.has(u.href) ? null : u.href;
      } catch (e) { return null; }
    }
    function prefetchUrl(href) {
      var u = canPrefetch(href);
      if (!u) return;
      prefetched.add(u);
      fetch(u, { credentials: 'same-origin', priority: 'low' }).catch(function () {});
    }
    ['pointerenter', 'touchstart', 'focusin'].forEach(function (evt) {
      document.addEventListener(evt, function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
        if (a) prefetchUrl(a.href);
      }, { capture: true, passive: true });
    });

    window.addEventListener('load', function () {
      var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (conn && conn.saveData) return;
      var warm = function () {
        var base = (document.body.getAttribute('data-base') || '/').replace(/\/+$/, '') + '/';
        var core = ['', 'venues/', 'venues-live/', 'venues-location/', 'venues-find/',
          'facilities/', 'facilities-green-room/', 'facilities-toilet/', 'facilities-water/', 'facilities-dining/',
          'media/', 'live-stream/', 'transportation/', 'transportation-bus/', 'transportation-auto/',
          'developers/', 'help/'].map(function (r) { return location.origin + base + r; });
        var list = core.concat(Array.from(document.querySelectorAll('a[href]')).map(function (a) { return a.href; }));
        var idx = 0;
        (function next() {
          if (idx >= list.length || prefetched.size >= 45) return;
          Promise.all(list.slice(idx, idx + 3).map(function (h) {
            var u = canPrefetch(h);
            if (!u) return Promise.resolve();
            prefetched.add(u);
            return fetch(u, { credentials: 'same-origin', priority: 'low' }).catch(function () {});
          })).then(function () { idx += 3; setTimeout(next, 120); });
        })();
      };
      if ('requestIdleCallback' in window) window.requestIdleCallback(warm, { timeout: 1200 });
      else setTimeout(warm, 400);
    });

    if ('serviceWorker' in navigator) {
      var swBase = (document.body.getAttribute('data-base') || '/').replace(/\/+$/, '');
      var hadCtrl = !!navigator.serviceWorker.controller, pendingReload = false;
      navigator.serviceWorker.addEventListener('message', function (ev) {
        if (!ev.data || ev.data.type !== 'KAL_SW_UPDATED') return;
        try {
          var prev = sessionStorage.getItem('kal_sw_ver');
          if (prev && prev !== ev.data.version && hadCtrl) pendingReload = true;
          sessionStorage.setItem('kal_sw_ver', ev.data.version);
        } catch (e) {}
      });
      navigator.serviceWorker.addEventListener('controllerchange', function () { if (hadCtrl) pendingReload = true; });
      document.addEventListener('click', function (ev) {
        if (!pendingReload) return;
        var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
        if (!a || a.target === '_blank') return;
        try {
          var u = new URL(a.href, location.origin);
          if (u.origin === location.origin) { pendingReload = false; ev.preventDefault(); location.assign(u.href); }
        } catch (e) {}
      }, true);
      window.addEventListener('load', function () {
        navigator.serviceWorker.register(swBase + '/sw.js', { updateViaCache: 'none' }).then(function (reg) {
          document.addEventListener('visibilitychange', function () { if (!document.hidden) reg.update().catch(function () {}); });
        }).catch(function () {});
      });
    }
  }
})();
