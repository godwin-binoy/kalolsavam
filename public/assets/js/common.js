/* Global Kalolsavam frontend core shared by public pages and staff portals. */
(function () {
  'use strict';

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

  function url(p) {
    return (!p || /^https?:\/\//i.test(p)) ? p : BASE + (p.charAt(0) === '/' ? p : '/' + p);
  }
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
  function normName(s) {
    return String(s || '').toLowerCase().replace(/^stage\s*\d+\s*[-—:.]?\s*/i, '').trim();
  }
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
})();
