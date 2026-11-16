(function(){
  'use strict';
  window.KalApp = { onCleanup: function(){} };

  var html = document.documentElement, themeBtn = document.getElementById('theme'),
      menu = document.getElementById('menu'), mnav = document.getElementById('mnav'),
      header = document.querySelector('.hdr'), dock = document.querySelector('.utility-dock');

  if (themeBtn){
    themeBtn.addEventListener('click', function(){
      var dark = html.classList.toggle('dark');
      try { localStorage.setItem('kal_theme', dark ? 'dark' : 'light'); } catch(e){}
    });
  }

  if (menu && mnav){
    function closeDrawer(){
      if (header) header.classList.remove('open');
      mnav.classList.remove('open');
      menu.setAttribute('aria-expanded', 'false');
      if (dock && window.pageYOffset <= 60) dock.classList.remove('dock-hidden');
    }
    function openDrawer(){
      if (header){
        var h = Math.ceil(mnav.getBoundingClientRect().height);
        if (h > 0) header.style.setProperty('--drawer-h', (h + 1) + 'px');
        header.classList.add('open');
      }
      if (dock) dock.classList.add('dock-hidden');
      mnav.classList.add('open');
      menu.setAttribute('aria-expanded', 'true');
    }
    menu.addEventListener('click', function(){ mnav.classList.contains('open') ? closeDrawer() : openDrawer(); });
    mnav.addEventListener('click', function(ev){ if (ev.target.closest('a')) closeDrawer(); });
    document.addEventListener('click', function(ev){
      if (mnav.classList.contains('open') && !mnav.contains(ev.target) && !menu.contains(ev.target)) closeDrawer();
    }, true);
    document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape' && mnav.classList.contains('open')) closeDrawer(); });
  }

  if (dock){
    var lastY = window.pageYOffset || document.documentElement.scrollTop || 0;
    window.addEventListener('scroll', function(){
      if (mnav && mnav.classList.contains('open')) return;
      var y = window.pageYOffset || document.documentElement.scrollTop || 0;
      if (y <= 40){ dock.classList.remove('dock-hidden'); lastY = y; return; }
      if (Math.abs(y - lastY) < 6) return;
      dock.classList.toggle('dock-hidden', y > lastY && y > 60);
      lastY = y;
    }, { passive: true });
  }

  // Aggressive background caching & intent prefetch
  var prefetched = new Set();
  function canPrefetch(href){
    if (!href || prefetched.size >= 45) return null;
    try {
      var u = new URL(href, location.origin);
      if (u.origin !== location.origin || (u.pathname === location.pathname && !u.search)) return null;
      if (/^\/(admin|stagemaster|dataworker|dashboard|api)\b/.test(u.pathname)) return null;
      if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(u.pathname)) return null;
      return prefetched.has(u.href) ? null : u.href;
    } catch(e){ return null; }
  }
  function prefetchUrl(href){
    var u = canPrefetch(href);
    if (!u) return;
    prefetched.add(u);
    fetch(u, { credentials: 'same-origin', priority: 'low' }).catch(function(){});
  }
  function onIntent(ev){
    var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
    if (a) prefetchUrl(a.href);
  }
  ['pointerenter', 'touchstart', 'focusin'].forEach(function(evt){
    document.addEventListener(evt, onIntent, { capture: true, passive: true });
  });

  window.addEventListener('load', function(){
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn && conn.saveData) return;
    var warm = function(){
      var base = (document.body.getAttribute('data-base') || '/').replace(/\/+$/, '') + '/';
      var core = ['', 'venues/', 'venues-live/', 'venues-location/', 'venues-find/',
        'facilities/', 'facilities-green-room/', 'facilities-toilet/', 'facilities-water/', 'facilities-dining/',
        'media/', 'live-stream/', 'transportation/', 'transportation-bus/', 'transportation-auto/',
        'developers/', 'help/'].map(function(r){ return location.origin + base + r; });
      var list = core.concat(Array.from(document.querySelectorAll('a[href]')).map(function(a){ return a.href; }));
      var idx = 0;
      (function next(){
        if (idx >= list.length || prefetched.size >= 45) return;
        Promise.all(list.slice(idx, idx + 3).map(function(h){
          var u = canPrefetch(h);
          if (!u) return Promise.resolve();
          prefetched.add(u);
          return fetch(u, { credentials: 'same-origin', priority: 'low' }).catch(function(){});
        })).then(function(){ idx += 3; setTimeout(next, 120); });
      })();
    };
    if ('requestIdleCallback' in window) window.requestIdleCallback(warm, { timeout: 1200 });
    else setTimeout(warm, 400);
  });

  if ('serviceWorker' in navigator){
    var swBase = (document.body.getAttribute('data-base') || '/').replace(/\/+$/, '');
    var hadCtrl = !!navigator.serviceWorker.controller, pendingReload = false;
    navigator.serviceWorker.addEventListener('message', function(ev){
      if (!ev.data || ev.data.type !== 'KAL_SW_UPDATED') return;
      try {
        var prev = sessionStorage.getItem('kal_sw_ver');
        if (prev && prev !== ev.data.version && hadCtrl) pendingReload = true;
        sessionStorage.setItem('kal_sw_ver', ev.data.version);
      } catch(e){}
    });
    navigator.serviceWorker.addEventListener('controllerchange', function(){ if (hadCtrl) pendingReload = true; });
    document.addEventListener('click', function(ev){
      if (!pendingReload) return;
      var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
      if (!a || a.target === '_blank') return;
      try {
        var u = new URL(a.href, location.origin);
        if (u.origin === location.origin){ pendingReload = false; ev.preventDefault(); location.assign(u.href); }
      } catch(e){}
    }, true);
    window.addEventListener('load', function(){
      navigator.serviceWorker.register(swBase + '/sw.js', { updateViaCache: 'none' }).then(function(reg){
        document.addEventListener('visibilitychange', function(){ if (!document.hidden) reg.update().catch(function(){}); });
      }).catch(function(){});
    });
  }
})();
