(function(){
  'use strict';
  var S = { onAuthLost: function(){} };
  var DEFAULT_API_ORIGIN = 'https://apikalolsavammala.dpdns.org';
  var TOKEN_KEY = 'kal_token';
  var REFRESH_KEY = 'kal_refresh_token';

  function resolveApiOrigin(){
    if (typeof window.KAL_API_BASE === 'string') return window.KAL_API_BASE.replace(/\/+$/, '');
    var meta = document.querySelector('meta[name="kal-api"]');
    if (meta && meta.content) return meta.content.replace(/\/+$/, '');
    if (location.port === '8000' || location.hostname === 'testserver' || location.hostname === 'apikalolsavammala.dpdns.org') return '';
    return DEFAULT_API_ORIGIN;
  }

  var API_ORIGIN = resolveApiOrigin();

  function apiUrl(path){
    if (!path || /^https?:\/\//i.test(path)) return path;
    return API_ORIGIN + (path.charAt(0) === '/' ? path : '/' + path);
  }

  function getToken(){
    try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch(e){ return ''; }
  }
  function setToken(t){
    try {
      if (t) sessionStorage.setItem(TOKEN_KEY, t);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch(e){}
  }
  function getRefreshToken(){
    try { return sessionStorage.getItem(REFRESH_KEY) || ''; } catch(e){ return ''; }
  }
  function setRefreshToken(t){
    try {
      if (t) sessionStorage.setItem(REFRESH_KEY, t);
      else sessionStorage.removeItem(REFRESH_KEY);
    } catch(e){}
  }
  function clearTokens(){
    setToken('');
    setRefreshToken('');
  }

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  var isRefreshing = false;
  var refreshSubscribers = [];

  function onRefreshed(newToken){
    refreshSubscribers.forEach(function(cb){ cb(newToken); });
    refreshSubscribers = [];
  }

  async function tryRefreshToken(){
    var rf = getRefreshToken();
    if (!rf) return null;
    try {
      var res = await fetch(apiUrl('/api/v1/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rf })
      });
      if (!res.ok) return null;
      var data = await res.json();
      if (data && data.access_token){
        setToken(data.access_token);
        if (data.refresh_token) setRefreshToken(data.refresh_token);
        return data.access_token;
      }
      return null;
    } catch(e){
      return null;
    }
  }

  async function raw(path, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    var token = getToken();
    if (token && !opts.headers['Authorization']){
      opts.headers['Authorization'] = 'Bearer ' + token;
    }
    var method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD'){
      if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)){
        opts.body = JSON.stringify(opts.body);
        opts.headers['Content-Type'] = 'application/json';
      }
    }
    opts.credentials = 'include';
    var res = await fetch(apiUrl(path), opts);
    var data = null;
    var ct = res.headers.get('content-type') || '';
    if (ct.indexOf('json') >= 0){ try { data = await res.json(); } catch(e){} }
    return { ok: res.ok, status: res.status, data: data, detail: data && (data.error || data.detail) };
  }

  async function api(path, opts){
    var r = await raw(path, opts);
    if (r.status === 401 && getRefreshToken() && path.indexOf('/auth/login') < 0 && path.indexOf('/auth/refresh') < 0){
      if (!isRefreshing){
        isRefreshing = true;
        var newToken = await tryRefreshToken();
        isRefreshing = false;
        if (newToken){
          onRefreshed(newToken);
          return await raw(path, opts);
        } else {
          clearTokens();
          S.onAuthLost();
          return r;
        }
      } else {
        return new Promise(function(resolve){
          refreshSubscribers.push(async function(){
            resolve(await raw(path, opts));
          });
        });
      }
    }

    if (r.status === 401){
      clearTokens();
      S.onAuthLost();
    }
    return r;
  }

  async function downloadBlob(path, filename){
    var hdrs = {};
    var token = getToken();
    if (token) hdrs['Authorization'] = 'Bearer ' + token;
    try {
      var res = await fetch(apiUrl(path), { method: 'GET', headers: hdrs, credentials: 'include' });
      if (!res.ok) throw new Error('Status ' + res.status);
      var blob = await res.blob();
      var u = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = u;
      a.download = filename || 'download.csv';
      document.body.appendChild(a);
      a.click();
      setTimeout(function(){ a.remove(); URL.revokeObjectURL(u); }, 1500);
      return true;
    } catch(e){
      window.KalAPI.toast('Download failed: ' + e.message, true);
      return false;
    }
  }

  function stream(path, handlers){
    handlers = handlers || {};
    var stopped = false;

    (async function loop(){
      while (!stopped){
        var alive = false;
        try {
          var hdrs = {};
          var token = getToken();
          if (token) hdrs['Authorization'] = 'Bearer ' + token;
          var res = await fetch(apiUrl(path), { method: 'GET', credentials: 'include', headers: hdrs });
          if (res.status === 401) {
            stopped = true;
            clearTokens();
            if (S.onAuthLost) S.onAuthLost();
            if (handlers.onmissed) handlers.onmissed();
            return;
          }
          if (!res.ok || !res.body) throw new Error('status ' + res.status);
          alive = true;
          if (handlers.onopen) handlers.onopen();
          var rd = res.body.getReader(), dec = new TextDecoder(), buf = '';
          for (;;){
            if (stopped) { try { rd.cancel(); } catch(e){} break; }
            var chunk = await rd.read();
            if (chunk.done) break;
            buf += dec.decode(chunk.value, { stream: true });
            var idx;
            while ((idx = buf.indexOf('\n\n')) >= 0){
              var frame = buf.slice(0, idx);
              buf = buf.slice(idx + 2);
              var lines = frame.split('\n');
              var isHeartbeat = lines.some(function(l){ return l.indexOf('event: heartbeat') === 0 || l.indexOf('event: hello') === 0; });
              if (isHeartbeat) continue;

              var line = lines.filter(function(l){ return l.indexOf('data:') === 0; })[0];
              if (!line) continue;
              var msg; try { msg = JSON.parse(line.slice(5).trim()); } catch(e){ continue; }
              if (handlers['*']) handlers['*'](msg);
              if (msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
            }
          }
        } catch(e){ /* retry */ }
        if (handlers.onmissed) handlers.onmissed();
        if (stopped) break;
        await new Promise(function(r){ setTimeout(r, alive ? 2500 : 6000); });
      }
    })();

    return { close: function(){ stopped = true; } };
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
    esc: esc,
    api: api,
    downloadBlob: downloadBlob,
    stream: stream,
    toast: function(text, isErr){
      var stack = document.querySelector('.toast-stack');
      if (!stack) {
        stack = document.createElement('div');
        stack.className = 'toast-stack';
        document.body.appendChild(stack);
      }
      var t = document.createElement('div');
      t.className = 'toast' + (isErr ? ' err' : '');
      t.textContent = text;
      stack.appendChild(t);
      setTimeout(function(){ t.remove(); }, 3500);
    }
  };
})();
