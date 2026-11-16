(function(){
  'use strict';
  window.KalApp = { onCleanup: function(){} };

  var html = document.documentElement;
  var KEY = 'kal_theme';
  var themeBtn = document.getElementById('theme');
  var menu = document.getElementById('menu');
  var mnav = document.getElementById('mnav');
  var header = document.querySelector('.hdr');
  var dock = document.querySelector('.utility-dock');

  if (themeBtn){
    themeBtn.addEventListener('click', function(){
      var dark = html.classList.toggle('dark');
      try { localStorage.setItem(KEY, dark ? 'dark' : 'light'); } catch(e){}
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
    menu.addEventListener('click', function(){
      if (mnav.classList.contains('open')) closeDrawer();
      else openDrawer();
    });
    mnav.addEventListener('click', function(ev){
      if (ev.target.closest('a')) closeDrawer();
    });
    document.addEventListener('click', function(ev){
      if (!mnav.classList.contains('open')) return;
      if (mnav.contains(ev.target) || menu.contains(ev.target)) return;
      closeDrawer();
    }, true);
    document.addEventListener('keydown', function(ev){
      if (ev.key === 'Escape' && mnav.classList.contains('open')) closeDrawer();
    });
  }

  // Organic hide/show for floating language + theme utility dock (header stays pinned)
  if (dock) {
    var lastScroll = window.pageYOffset || document.documentElement.scrollTop || 0;
    window.addEventListener('scroll', function() {
      if (mnav && mnav.classList.contains('open')) return;
      var currentScroll = window.pageYOffset || document.documentElement.scrollTop || 0;
      if (currentScroll <= 40) {
        dock.classList.remove('dock-hidden');
        lastScroll = currentScroll;
        return;
      }
      if (Math.abs(currentScroll - lastScroll) < 6) return;
      if (currentScroll > lastScroll && currentScroll > 60) {
        dock.classList.add('dock-hidden');
      } else {
        dock.classList.remove('dock-hidden');
      }
      lastScroll = currentScroll;
    }, { passive: true });
  }

  // Smart prefetch (hover, touchstart, focusin + idle nav warmup) for instant switches
  var prefetched = new Set();
  function prefetchUrl(href){
    if (!href || prefetched.size >= 40) return;
    try {
      var u = new URL(href, location.origin);
      if (u.origin !== location.origin) return;
      if (u.pathname === location.pathname && !u.search) return;
      if (u.pathname.startsWith('/admin') || u.pathname.startsWith('/stagemaster') ||
          u.pathname.startsWith('/dataworker') || u.pathname.startsWith('/dashboard') ||
          u.pathname.startsWith('/api')) return;
      if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(u.pathname)) return;
      if (prefetched.has(u.href)) return;
      prefetched.add(u.href);
      fetch(u.href, { credentials: 'same-origin', priority: 'low' }).catch(function(){});
    } catch(e){}
  }

  function onLinkIntent(ev){
    var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
    if (a) prefetchUrl(a.href);
  }
  document.addEventListener('pointerenter', onLinkIntent, { capture: true, passive: true });
  document.addEventListener('touchstart', onLinkIntent, { capture: true, passive: true });
  document.addEventListener('focusin', onLinkIntent, { capture: true, passive: true });

  window.addEventListener('load', function(){
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn && conn.saveData) return;

    var warmQueue = function(){
      var basePath = (document.body.getAttribute('data-base') || '/').replace(/\/+$/, '') + '/';
      var coreRoutes = [
        '', 'venues/', 'venues-live/', 'venues-location/', 'venues-find/',
        'facilities/', 'facilities-green-room/', 'facilities-toilet/',
        'facilities-water/', 'facilities-dining/', 'media/', 'live-stream/',
        'transportation/', 'transportation-bus/', 'transportation-auto/',
        'developers/', 'help/'
      ].map(function(r){ return location.origin + basePath + r; });

      var pageLinks = Array.from(document.querySelectorAll('a[href]')).map(function(a){ return a.href; });
      var all = coreRoutes.concat(pageLinks).filter(function(h){
        try {
          var u = new URL(h, location.origin);
          if (u.origin !== location.origin) return false;
          if (u.pathname.startsWith('/admin') || u.pathname.startsWith('/stagemaster') ||
              u.pathname.startsWith('/dataworker') || u.pathname.startsWith('/dashboard') ||
              u.pathname.startsWith('/api')) return false;
          if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(u.pathname)) return false;
          return !prefetched.has(u.href);
        } catch(e){ return false; }
      });

      var idx = 0;
      function nextBatch(){
        if (idx >= all.length || prefetched.size >= 45) return;
        var batch = all.slice(idx, idx + 3);
        idx += 3;
        Promise.all(batch.map(function(u){
          if (prefetched.has(u)) return Promise.resolve();
          prefetched.add(u);
          return fetch(u, { credentials: 'same-origin', priority: 'low' }).catch(function(){});
        })).then(function(){
          setTimeout(nextBatch, 150);
        });
      }
      nextBatch();
    };
    if ('requestIdleCallback' in window) window.requestIdleCallback(warmQueue, { timeout: 1200 });
    else setTimeout(warmQueue, 400);
  });

  // Service Worker registration with updateViaCache:none + automatic update handling
  if ('serviceWorker' in navigator){
    var rawBase = document.body.getAttribute('data-base') || '/';
    var swBase = rawBase.replace(/\/+$/, '');
    var hadController = !!navigator.serviceWorker.controller;
    var pendingReload = false;

    navigator.serviceWorker.addEventListener('message', function(ev){
      if (!ev.data || ev.data.type !== 'KAL_SW_UPDATED') return;
      try {
        var prevVer = sessionStorage.getItem('kal_sw_ver');
        if (prevVer && prevVer !== ev.data.version && hadController) {
          pendingReload = true;
        }
        sessionStorage.setItem('kal_sw_ver', ev.data.version);
      } catch(e){}
    });

    navigator.serviceWorker.addEventListener('controllerchange', function(){
      if (hadController) pendingReload = true;
    });

    // If a new SW build arrived while user was reading, reload cleanly on next navigation
    document.addEventListener('click', function(ev){
      if (!pendingReload) return;
      var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
      if (!a || a.target === '_blank') return;
      try {
        var u = new URL(a.href, location.origin);
        if (u.origin === location.origin) {
          pendingReload = false;
          ev.preventDefault();
          location.assign(u.href);
        }
      } catch(e){}
    }, true);

    window.addEventListener('load', function(){
      navigator.serviceWorker.register(swBase + '/sw.js', { updateViaCache: 'none' })
        .then(function(reg){
          document.addEventListener('visibilitychange', function(){
            if (!document.hidden) reg.update().catch(function(){});
          });
        })
        .catch(function(){});
    });
  }
})();
