/* Kalolsavam staff API client: auth, single-flight refresh, SSE, downloads. */
(function () {
  'use strict';

  var S = { onAuthLost: function () {} };
  var DEFAULT_API_ORIGIN = 'https://apikalolsavammala.dpdns.org';
  var TOKEN_KEY = 'kal_token';
  var REFRESH_KEY = 'kal_refresh_token';
  var AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/register'];

  function resolveApiOrigin() {
    var body = document.body;
    var explicit = body && body.getAttribute('data-api');
    if (explicit === 'same-origin' || explicit === '') return '';
    if (explicit != null) return explicit.replace(/\/+$/, '');
    if (typeof window.KAL_API_BASE === 'string') {
      if (window.KAL_API_BASE === 'same-origin') return '';
      return window.KAL_API_BASE.replace(/\/+$/, '');
    }
    var meta = document.querySelector('meta[name="kal-api"]');
    if (meta && meta.content) {
      if (meta.content === 'same-origin') return '';
      return meta.content.replace(/\/+$/, '');
    }
    if (location.port === '8000' || location.hostname === 'testserver' ||
        location.hostname === 'apikalolsavammala.dpdns.org') return '';
    return DEFAULT_API_ORIGIN;
  }
  var API_ORIGIN = resolveApiOrigin();

  function apiUrl(path) {
    if (!path || /^https?:\/\//i.test(path)) return path;
    return API_ORIGIN + (path.charAt(0) === '/' ? path : '/' + path);
  }

  function isAuthPath(path) {
    var p = String(path || '');
    for (var i = 0; i < AUTH_PATHS.length; i++) {
      if (p.indexOf(AUTH_PATHS[i]) >= 0) return true;
    }
    return false;
  }

  function read(key) { try { return sessionStorage.getItem(key) || ''; } catch (e) { return ''; } }
  function write(key, val) {
    try {
      if (val) sessionStorage.setItem(key, val);
      else sessionStorage.removeItem(key);
    } catch (e) {}
  }
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

  function hasOwn(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function shallow(o) {
    var out = {};
    if (o) for (var k in o) if (hasOwn(o, k)) out[k] = o[k];
    return out;
  }
  function findHeader(headers, name) {
    var lower = name.toLowerCase();
    for (var k in headers) if (hasOwn(headers, k) && k.toLowerCase() === lower) return k;
    return null;
  }
  function setHeader(headers, name, value) {
    var existing = findHeader(headers, name);
    if (existing) delete headers[existing];
    if (value != null && value !== '') headers[name] = value;
  }

  /* Build the request ONCE (body serialised here), then clone per attempt so a
     retry can never inherit a stale Authorization header or a consumed body. */
  function prepare(opts) {
    var o = shallow(opts);
    o.headers = shallow(opts && opts.headers);
    o.method = (o.method || 'GET').toUpperCase();
    var b = o.body;
    var plain = b && typeof b === 'object' &&
      !(typeof FormData !== 'undefined' && b instanceof FormData) &&
      !(typeof Blob !== 'undefined' && b instanceof Blob) &&
      !(typeof URLSearchParams !== 'undefined' && b instanceof URLSearchParams);
    if (plain) {
      o.body = JSON.stringify(b);
      if (!findHeader(o.headers, 'content-type')) setHeader(o.headers, 'Content-Type', 'application/json');
    }
    o.credentials = 'include';
    return o;
  }

  function withAuth(prepared) {
    var o = shallow(prepared);
    o.headers = shallow(prepared.headers);
    var token = getToken();
    setHeader(o.headers, 'Authorization', token ? 'Bearer ' + token : null);
    return o;
  }

  var refreshPromise = null;

  async function doRefresh() {
    var rf = getRefreshToken();
    if (!rf) return null;
    var res;
    try {
      res = await fetch(apiUrl('/api/v1/auth/refresh'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rf })
      });
    } catch (e) { return null; }
    if (!res.ok) return null;
    var data = null;
    try { data = await res.json(); } catch (e) { return null; }
    if (!data || !data.access_token) return null;
    setToken(data.access_token);
    if (data.refresh_token) setRefreshToken(data.refresh_token);
    return data.access_token;
  }

  /* Single flight: every concurrent 401 awaits the SAME promise, then re-reads
     the token from storage. No subscriber queue => nothing can hang. */
  function refreshOnce() {
    if (!refreshPromise) {
      refreshPromise = doRefresh().then(
        function (t) { refreshPromise = null; return t; },
        function () { refreshPromise = null; return null; }
      );
    }
    return refreshPromise;
  }

  async function send(path, prepared) {
    var res = await fetch(apiUrl(path), withAuth(prepared));
    var data = null;
    var ct = res.headers.get('content-type') || '';
    if (ct.indexOf('json') >= 0) { try { data = await res.json(); } catch (e) {} }
    return {
      ok: res.ok,
      status: res.status,
      data: data,
      detail: data && (data.error || data.detail)
    };
  }

  async function api(path, opts) {
    var prepared = prepare(opts);
    var r = await send(path, prepared);
    if (r.status === 401 && !isAuthPath(path) && getRefreshToken()) {
      var t = await refreshOnce();
      if (t) r = await send(path, prepared);
    }
    if (r.status === 401 && !isAuthPath(path)) {
      clearTokens();
      S.onAuthLost();
    }
    return r;
  }

  async function authorizedFetch(path, opts) {
    var prepared = prepare(opts);
    var res = await fetch(apiUrl(path), withAuth(prepared));
    if (res.status === 401 && !isAuthPath(path) && getRefreshToken()) {
      var t = await refreshOnce();
      if (t) res = await fetch(apiUrl(path), withAuth(prepared));
    }
    return res;
  }

  async function downloadBlob(path, filename) {
    try {
      var res = await authorizedFetch(path, { method: 'GET' });
      if (!res.ok) throw new Error('Status ' + res.status);
      var blob = await res.blob();
      var u = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = u;
      a.download = filename || 'download.csv';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { a.remove(); URL.revokeObjectURL(u); }, 1500);
      return true;
    } catch (e) {
      toast('Download failed: ' + e.message, true);
      return false;
    }
  }

  function dispatchFrame(frame, handlers) {
    var lines = frame.split('\n');
    var evt = '';
    var dataLines = [];
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i];
      if (l.indexOf('event:') === 0) evt = l.slice(6).trim();
      else if (l.indexOf('data:') === 0) dataLines.push(l.slice(5).trim());
    }
    if (evt === 'heartbeat' || evt === 'hello' || !dataLines.length) return;
    var msg;
    try { msg = JSON.parse(dataLines.join('\n')); } catch (e) { return; }
    if (handlers['*']) handlers['*'](msg);
    if (msg && msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
  }

  function stream(path, handlers) {
    handlers = handlers || {};
    var stopped = false;
    var controller = null;

    (async function loop() {
      var delay = 2500;
      while (!stopped) {
        var opened = false;
        try {
          controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
          var res = await authorizedFetch(path, {
            method: 'GET',
            signal: controller ? controller.signal : undefined
          });
          if (res.status === 401) {
            clearTokens();
            if (handlers.onmissed) handlers.onmissed();
            S.onAuthLost();
            return;
          }
          if (!res.ok || !res.body) throw new Error('status ' + res.status);
          opened = true;
          if (handlers.onopen) handlers.onopen();

          var rd = res.body.getReader();
          var dec = new TextDecoder();
          var buf = '';
          while (!stopped) {
            var chunk = await rd.read();
            if (chunk.done) break;
            buf += dec.decode(chunk.value, { stream: true });
            var idx;
            while ((idx = buf.indexOf('\n\n')) >= 0) {
              var frame = buf.slice(0, idx);
              buf = buf.slice(idx + 2);
              dispatchFrame(frame, handlers);
            }
          }
          try { rd.cancel(); } catch (e) {}
        } catch (e) { /* reconnect */ }

        if (stopped) break;
        if (handlers.onmissed) handlers.onmissed();
        delay = opened ? 2500 : Math.min(delay * 2, 15000);
        await new Promise(function (r) { setTimeout(r, delay); });
      }
    })();

    return {
      close: function () {
        stopped = true;
        if (controller) { try { controller.abort(); } catch (e) {} }
      }
    };
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
    state: S,
    apiOrigin: API_ORIGIN,
    url: apiUrl,
    getToken: getToken,
    setToken: setToken,
    getRefreshToken: getRefreshToken,
    setRefreshToken: setRefreshToken,
    clearTokens: clearTokens,
    refresh: refreshOnce,
    esc: esc,
    api: api,
    downloadBlob: downloadBlob,
    stream: stream,
    toast: toast
  };
})();
