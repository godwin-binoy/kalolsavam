(function(){
  'use strict';
  var S = { onAuthLost: function(){} };

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  async function raw(path, opts){
    opts = opts || {};
    opts.headers = opts.headers || {};
    var method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD'){
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
    return { ok: res.ok, status: res.status, data: data, detail: data && (data.error || data.detail) };
  }

  async function api(path, opts){
    var r = await raw(path, opts);
    if (r.status === 401) S.onAuthLost();
    return r;
  }

  function stream(path, handlers){
    handlers = handlers || {};
    var stopped = false;

    (async function loop(){
      while (!stopped){
        var alive = false;
        try {
          var res = await fetch(path, { method: 'GET', credentials: 'include' });
          if (res.status === 401) {
            stopped = true;
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
    esc: esc,
    api: api,
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
