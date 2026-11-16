/* Kalolsavam staff API client: auth, single-flight refresh, SSE, downloads. */
(function () {
  'use strict';

  var S = { onAuthLost: function () {} };
  var DEFAULT_API_ORIGIN = 'https://apikalolsavammala.dpdns.org';
  var TOKEN_KEY = 'kal_token', REFRESH_KEY = 'kal_refresh_token';
  var AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/register'];

  var API_ORIGIN = (function () {
    var explicit = document.body && document.body.getAttribute('data-api');
    if (explicit === 'same-origin' || explicit === '') return '';
    if (explicit != null) return explicit.replace(/\/+$/, '');
    if (typeof window.KAL_API_BASE === 'string') {
      return window.KAL_API_BASE === 'same-origin' ? '' : window.KAL_API_BASE.replace(/\/+$/, '');
    }
    var meta = document.querySelector('meta[name="kal-api"]');
    if (meta && meta.content) return meta.content === 'same-origin' ? '' : meta.content.replace(/\/+$/, '');
    if (location.port === '8000' || location.hostname === 'testserver' || location.hostname === 'apikalolsavammala.dpdns.org') return '';
    return DEFAULT_API_ORIGIN;
  })();

  function apiUrl(path) {
    return (!path || /^https?:\/\//i.test(path)) ? path : API_ORIGIN + (path.charAt(0) === '/' ? path : '/' + path);
  }
  function isAuthPath(path) {
    var p = String(path || '');
    return AUTH_PATHS.some(function (x) { return p.indexOf(x) >= 0; });
  }
  function read(k) { try { return sessionStorage.getItem(k) || ''; } catch (e) { return ''; } }
  function write(k, v) { try { if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k); } catch (e) {} }
  function getToken() { return read(TOKEN_KEY); }
  function setToken(t) { write(TOKEN_KEY, t); }
  function getRefreshToken() { return read(REFRESH_KEY); }
  function setRefreshToken(t) { write(REFRESH_KEY, t); }
  function clearTokens() { setToken(''); setRefreshToken(''); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function prepare(opts) {
    var o = Object.assign({}, opts || {});
    o.headers = Object.assign({}, (opts && opts.headers) || {});
    o.method = (o.method || 'GET').toUpperCase();
    var b = o.body;
    var isPlain = b && typeof b === 'object' &&
      !(typeof FormData !== 'undefined' && b instanceof FormData) &&
      !(typeof Blob !== 'undefined' && b instanceof Blob) &&
      !(typeof URLSearchParams !== 'undefined' && b instanceof URLSearchParams);
    if (isPlain) {
      o.body = JSON.stringify(b);
      if (!Object.keys(o.headers).some(function (k) { return k.toLowerCase() === 'content-type'; })) {
        o.headers['Content-Type'] = 'application/json';
      }
    }
    o.credentials = 'include';
    return o;
  }

  function withAuth(prepared) {
    var o = Object.assign({}, prepared);
    o.headers = Object.assign({}, prepared.headers);
    Object.keys(o.headers).forEach(function (k) { if (k.toLowerCase() === 'authorization') delete o.headers[k]; });
    var t = getToken();
    if (t) o.headers.Authorization = 'Bearer ' + t;
    return o;
  }

  var refreshPromise = null;
  async function doRefresh() {
    var rf = getRefreshToken();
    if (!rf) return null;
    try {
      var res = await fetch(apiUrl('/api/v1/auth/refresh'), {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rf })
      });
      if (!res.ok) return null;
      var data = await res.json().catch(function () { return null; });
      if (!data || !data.access_token) return null;
      setToken(data.access_token);
      if (data.refresh_token) setRefreshToken(data.refresh_token);
      return data.access_token;
    } catch (e) { return null; }
  }

  function refreshOnce() {
    if (!refreshPromise) refreshPromise = doRefresh().finally(function () { refreshPromise = null; });
    return refreshPromise;
  }

  async function authorizedFetch(path, opts) {
    var prep = prepare(opts);
    var res = await fetch(apiUrl(path), withAuth(prep));
    if (res.status === 401 && !isAuthPath(path) && getRefreshToken() && await refreshOnce()) {
      res = await fetch(apiUrl(path), withAuth(prep));
    }
    return res;
  }

  async function api(path, opts) {
    var res = await authorizedFetch(path, opts);
    if (res.status === 401 && !isAuthPath(path)) { clearTokens(); S.onAuthLost(); }
    var data = null;
    if ((res.headers.get('content-type') || '').indexOf('json') >= 0) {
      try { data = await res.json(); } catch (e) {}
    }
    return { ok: res.ok, status: res.status, data: data, detail: data && (data.error || data.detail) };
  }

  async function downloadBlob(path, filename) {
    try {
      var res = await authorizedFetch(path, { method: 'GET' });
      if (!res.ok) throw new Error('Status ' + res.status);
      var u = URL.createObjectURL(await res.blob());
      var a = document.createElement('a');
      a.href = u; a.download = filename || 'download.csv';
      document.body.appendChild(a); a.click();
      setTimeout(function () { a.remove(); URL.revokeObjectURL(u); }, 1500);
      return true;
    } catch (e) {
      toast('Download failed: ' + e.message, true);
      return false;
    }
  }

  function dispatchFrame(frame, handlers) {
    var evt = '', dataLines = [];
    frame.split('\n').forEach(function (l) {
      if (l.indexOf('event:') === 0) evt = l.slice(6).trim();
      else if (l.indexOf('data:') === 0) dataLines.push(l.slice(5).trim());
    });
    if (evt === 'heartbeat' || evt === 'hello' || !dataLines.length) return;
    try {
      var msg = JSON.parse(dataLines.join('\n'));
      if (handlers['*']) handlers['*'](msg);
      if (msg && msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
    } catch (e) {}
  }

  function stream(path, handlers) {
    handlers = handlers || {};
    var stopped = false, controller = null;
    (async function loop() {
      var delay = 2500;
      while (!stopped) {
        var opened = false;
        try {
          controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
          var res = await authorizedFetch(path, { method: 'GET', signal: controller ? controller.signal : undefined });
          if (res.status === 401) { clearTokens(); if (handlers.onmissed) handlers.onmissed(); S.onAuthLost(); return; }
          if (!res.ok || !res.body) throw new Error('status ' + res.status);
          opened = true;
          if (handlers.onopen) handlers.onopen();
          var rd = res.body.getReader(), dec = new TextDecoder(), buf = '';
          while (!stopped) {
            var chunk = await rd.read();
            if (chunk.done) break;
            buf += dec.decode(chunk.value, { stream: true });
            var idx;
            while ((idx = buf.indexOf('\n\n')) >= 0) {
              dispatchFrame(buf.slice(0, idx), handlers);
              buf = buf.slice(idx + 2);
            }
          }
          try { rd.cancel(); } catch (e) {}
        } catch (e) {}
        if (stopped) break;
        if (handlers.onmissed) handlers.onmissed();
        delay = opened ? 2500 : Math.min(delay * 2, 15000);
        await new Promise(function (r) { setTimeout(r, delay); });
      }
    })();
    return { close: function () { stopped = true; if (controller) try { controller.abort(); } catch (e) {} } };
  }

  function toast(text, isErr) {
    var stack = document.querySelector('.toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'toast-stack';
      stack.setAttribute('role', 'status');
      stack.setAttribute('aria-live', 'polite');
      document.body.appendChild(stack);
    }
    var t = document.createElement('div');
    t.className = 'toast' + (isErr ? ' err' : '');
    t.textContent = text;
    stack.appendChild(t);
    setTimeout(function () { t.remove(); }, 3500);
  }

  window.KalAPI = {
    state: S, apiOrigin: API_ORIGIN, url: apiUrl,
    getToken: getToken, setToken: setToken, getRefreshToken: getRefreshToken,
    setRefreshToken: setRefreshToken, clearTokens: clearTokens, refresh: refreshOnce,
    esc: esc, api: api, authorizedFetch: authorizedFetch, downloadBlob: downloadBlob,
    stream: stream, toast: toast
  };
})();
