(function(){
  'use strict';
  var S = { onAuthLost: function(){} };

  function csrf(){
    var m = document.cookie.match(/(?:^|; )kal_csrf=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  async function raw(path, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    var method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD'){
      var t = csrf(); if (t) opts.headers['X-CSRF-Token'] = t;
      if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)){
        opts.body = JSON.stringify(opts.body);
        opts.headers['Content-Type'] = 'application/json';
      }
    }
    opts.credentials = 'include';
    var res = await fetch(path, opts);
    var data = null;
    var ct = res.headers.get('content-type') || '';
    if (ct.indexOf('json') >= 0){ try { data = await res.json(); } catch(e){} }
    return { ok: res.ok, status: res.status, data: data, detail: data && data.error };
  }

  async function api(path, opts){
    var r = await raw(path, opts);
    if (r.status === 401) S.onAuthLost();
    return r;
  }

  async function sseLoop(path, handlers){
    while (!sseLoop._stop){
      var alive = false;
      try {
        var res = await fetch(path, { method: 'GET', credentials: 'include' });
        if (!res.ok || !res.body) throw new Error('status ' + res.status);
        alive = true;
        if (handlers.onopen) handlers.onopen();
        var rd = res.body.getReader(), dec = new TextDecoder(), buf = '';
        for (;;){
          var chunk = await rd.read();
          if (chunk.done) break;
          buf += dec.decode(chunk.value, { stream: true });
          var idx;
          while ((idx = buf.indexOf('\n\n')) >= 0){
            var frame = buf.slice(0, idx); buf = buf.slice(idx + 2);
            var line = frame.split('\n').filter(function(l){ return l.indexOf('data:') === 0; })[0];
            if (!line) continue;
            var msg; try { msg = JSON.parse(line.slice(5).trim()); } catch(e){ continue; }
            if (handlers['*']) handlers['*'](msg);
            if (msg.entity && handlers[msg.entity]) handlers[msg.entity](msg);
          }
        }
      } catch(e){ /* retry */ }
      if (handlers.onmissed) handlers.onmissed();
      if (sseLoop._stop) break;
      await new Promise(function(r){ setTimeout(r, alive ? 2500 : 6000); });
    }
  }

  function stream(path, handlers){
    sseLoop._stop = false;
    sseLoop(path, handlers || {});
    return { close: function(){ sseLoop._stop = true; } };
  }

  window.KalAPI = {
    state: S,
    api: api,
    stream: stream,
    toast: function(text, isErr){
      var t = document.createElement('div');
      t.className = 'toast' + (isErr ? ' err' : '');
      t.textContent = text;
      document.body.appendChild(t);
      setTimeout(function(){ t.remove(); }, 3500);
    }
  };
})();
