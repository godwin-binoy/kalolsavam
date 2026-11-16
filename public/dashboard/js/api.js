/* Staff API client built on window.Kal: Bearer + single-flight refresh, req(), SSE, downloads. */
(function () {
  'use strict';

  var K = window.Kal;
  var S = { onAuthLost: function () {} };
  var TOKEN_KEY = 'kal_token', REFRESH_KEY = 'kal_refresh_token';
  var AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/register'];

  function read(k) { try { return sessionStorage.getItem(k) || ''; } catch (e) { return ''; } }
  function write(k, v) { try { if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k); } catch (e) {} }
  function getToken() { return read(TOKEN_KEY); }
  function setToken(t) { write(TOKEN_KEY, t); }
  function getRefreshToken() { return read(REFRESH_KEY); }
  function setRefreshToken(t) { write(REFRESH_KEY, t); }
  function clearTokens() { setToken(''); setRefreshToken(''); }
  function isAuthPath(p) { return AUTH_PATHS.some(function (x) { return String(p || '').indexOf(x) >= 0; }); }

  function prepare(opts) {
    var o = Object.assign({ credentials: 'include' }, opts || {});
    o.headers = Object.assign({}, (opts && opts.headers) || {});
    o.method = (o.method || 'GET').toUpperCase();
    var b = o.body;
    var isPlain = b && typeof b === 'object' && !(b instanceof FormData) && !(b instanceof Blob) && !(b instanceof URLSearchParams);
    if (isPlain) {
      o.body = JSON.stringify(b);
      if (!Object.keys(o.headers).some(function (k) { return k.toLowerCase() === 'content-type'; })) {
        o.headers['Content-Type'] = 'application/json';
      }
    }
    return o;
  }

  function withAuth(prep) {
    var o = Object.assign({}, prep, { headers: Object.assign({}, prep.headers) });
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
      var res = await fetch(K.url('/api/v1/auth/refresh'), {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rf })
      });
      if (!res.ok) return null;
      var d = await res.json().catch(function () { return null; });
      if (!d || !d.access_token) return null;
      setToken(d.access_token);
      if (d.refresh_token) setRefreshToken(d.refresh_token);
      return d.access_token;
    } catch (e) { return null; }
  }
  function refreshOnce() {
    if (!refreshPromise) refreshPromise = doRefresh().finally(function () { refreshPromise = null; });
    return refreshPromise;
  }

  async function authorizedFetch(path, opts) {
    var prep = prepare(opts);
    var res = await fetch(K.url(path), withAuth(prep));
    if (res.status === 401 && !isAuthPath(path) && getRefreshToken() && await refreshOnce()) {
      res = await fetch(K.url(path), withAuth(prep));
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

  async function req(path, opts, okMsg) {
    var r = await api(path, opts);
    if (!r.ok) { toast('Failed: ' + (r.detail || r.status), true); return null; }
    if (okMsg) toast(okMsg);
    return r.data || true;
  }

  async function downloadBlob(path, filename) {
    try {
      var res = await authorizedFetch(path, { method: 'GET' });
      if (!res.ok) throw new Error('Status ' + res.status);
      var u = URL.createObjectURL(await res.blob()), a = document.createElement('a');
      a.href = u; a.download = filename || 'download.csv';
      document.body.appendChild(a); a.click();
      setTimeout(function () { a.remove(); URL.revokeObjectURL(u); }, 1500);
      return true;
    } catch (e) { toast('Download failed: ' + e.message, true); return false; }
  }

  function stream(path, handlers) {
    handlers = handlers || {};
    var stopped = false, ctrl = null;
    (async function loop() {
      var delay = 2500;
      while (!stopped) {
        var opened = false;
        try {
          ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
          var res = await authorizedFetch(path, { method: 'GET', signal: ctrl ? ctrl.signal : undefined });
          if (res.status === 401) { clearTokens(); if (handlers.onmissed) handlers.onmissed(); S.onAuthLost(); return; }
          if (!res.ok || !res.body) throw new Error('status ' + res.status);
          opened = true;
          if (handlers.onopen) handlers.onopen();
          var rd = res.body.getReader(), dec = new TextDecoder(), buf = '';
          while (!stopped) {
            var ch = await rd.read();
            if (ch.done) break;
            buf += dec.decode(ch.value, { stream: true });
            var idx;
            while ((idx = buf.indexOf('\n\n')) >= 0) {
              var frame = buf.slice(0, idx), evt = '', dl = [];
              buf = buf.slice(idx + 2);
              frame.split('\n').forEach(function (l) {
                if (l.indexOf('event:') === 0) evt = l.slice(6).trim();
                else if (l.indexOf('data:') === 0) dl.push(l.slice(5).trim());
              });
              if (evt !== 'heartbeat' && evt !== 'hello' && dl.length) {
                try {
                  var msg = JSON.parse(dl.join('\n'));
                  if (handlers['*']) handlers['*'](msg);
                  if (msg && msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
                } catch (e) {}
              }
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
    return { close: function () { stopped = true; if (ctrl) try { ctrl.abort(); } catch (e) {} } };
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
    state: S, apiOrigin: K.apiBase(), url: K.url, esc: K.esc, el: K.el, on: K.on, debounce: K.debounce,
    getToken: getToken, setToken: setToken, getRefreshToken: getRefreshToken, setRefreshToken: setRefreshToken,
    clearTokens: clearTokens, refresh: refreshOnce, api: api, req: req,
    authorizedFetch: authorizedFetch, downloadBlob: downloadBlob, stream: stream, toast: toast
  };
})();
