/* Thin fetch wrapper for the Kalolsavam backend.
 * - Attaches the Bearer access token, refreshing it transparently once on 401.
 * - Sends the CSRF double-submit header on unsafe methods.
 * - Never throws on HTTP errors: returns {ok, status, data|detail}. */
(function () {
  'use strict';

  var S = {
    access: '',
    csrf: '',
    onAuthLost: function () {}   // set by auth.js -> bounce to login view
  };

  function b64urlJson(tok) {
    try {
      var p = tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      while (p.length % 4) p += '=';
      return JSON.parse(decodeURIComponent(escape(atob(p))));
    } catch (e) { return null; }
  }

  function accessExpiringSoon(skewSec) {
    var c = b64urlJson(S.access);
    if (!c || !c.exp) return true;
    return (c.exp - skewSec) * 1000 < Date.now();
  }

  async function raw(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    if (S.access) opts.headers['Authorization'] = 'Bearer ' + S.access;
    var m = (opts.method || 'GET').toUpperCase();
    if (m !== 'GET' && m !== 'HEAD') {
      opts.headers['X-CSRF-Token'] = S.csrf;
      if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(opts.body);
        opts.headers['Content-Type'] = 'application/json';
      }
    }
    opts.credentials = 'include';
    var res = await fetch(path, opts);
    var data = null;
    var ct = res.headers.get('content-type') || '';
    if (ct.indexOf('json') >= 0) { try { data = await res.json(); } catch (e) {} }
    return { ok: res.ok, status: res.status, data: data,
             detail: data && data.detail };
  }

  async function refresh() {
    // /api/auth/refresh is cookie-driven and CSRF-guarded (double submit),
    // so we send the current X-CSRF-Token header with it. The server rotates
    // both cookies and returns the fresh csrf value, which we must adopt.
    var r = await raw('/api/auth/refresh', { method: 'POST', headers: {} });
    if (r.ok && r.data && r.data.access) {
      S.access = r.data.access;
      if (r.data.csrf) { S.csrf = r.data.csrf; }
      return true;
    }
    return false;
  }

  async function api(path, opts) {
    if (S.access && accessExpiringSoon(30)) { await refresh(); }
    var r = await raw(path, opts);
    if ((r.status === 401) && S.access) {     // token died mid-flight
      if (await refresh()) r = await raw(path, opts);
      else { S.onAuthLost(); }
    }
    return r;
  }

  /* Live change feed via SSE. The backend streams require an Authorization
   * header (EventSource cannot send one), so we consume them with fetch +
   * ReadableStream and parse "event: change\ndata: {...}\n\n" frames.
   * Handlers are keyed by entity name plus '*' for all events.
   * Auto-reconnects; on (re)connect the caller should re-fetch its snapshot. */
  var streamSeq = 0;   // per-page unique id, survives any close/reopen

  async function sseLoop(tag, path, handlers) {
    while (!sseLoop._stop) {
      var alive = false;
      try {
        var res = await fetch(path, {
          method: 'GET', credentials: 'include',
          headers: S.access ? { 'Authorization': 'Bearer ' + S.access } : {}
        });
        if (!res.ok || !res.body) throw new Error('status ' + res.status);
        alive = true;
        if (handlers.onopen) handlers.onopen();
        var rd = res.body.getReader(), dec = new TextDecoder(), buf = '';
        for (;;) {
          var chunk = await rd.read();
          if (chunk.done) break;
          buf += dec.decode(chunk.value, { stream: true });
          var idx;
          while ((idx = buf.indexOf('\n\n')) >= 0) {
            var frame = buf.slice(0, idx); buf = buf.slice(idx + 2);
            var line = frame.split('\n').filter(function (l) {
              return l.indexOf('data:') === 0; })[0];
            if (!line) continue;                       // keep-alive comment
            var msg;
            try { msg = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
            if (handlers['*']) handlers['*'](msg);
            if (msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
          }
        }
      } catch (e) { /* fall through to retry */ }
      // Only report the drop if this loop is still the current one — a stale
      // loop woken by stream.close() must never overwrite the new stream's
      // "live" badge or double-reconnect.
      if (streamSeq === tag && handlers.onmissed) handlers.onmissed();
      if (sseLoop._stop || streamSeq !== tag) break;
      await new Promise(function (r) { setTimeout(r, alive ? 2500 : 6000); });
    }
  }

  function stream(path, handlers) {
    sseLoop._stop = false;
    var tag = ++streamSeq;
    sseLoop(tag, path, handlers || {});
    return { close: function () { sseLoop._stop = true; } };
  }

  window.KalAPI = {
    state: S,
    api: api,
    stream: stream,
    refresh: refresh,
    toast: function (text, isErr) {
      var t = document.createElement('div');
      t.className = 'toast' + (isErr ? ' err' : '');
      t.textContent = text;
      document.body.appendChild(t);
      setTimeout(function () { t.remove(); }, 3500);
    },
    setTokens: function (access, csrf) { S.access = access || ''; S.csrf = csrf || ''; },
    clear: function () { S.access = ''; S.csrf = ''; }
  };
})();
