(function(){
  'use strict';
  window.KalApp = { onCleanup: function(){} };

  var html = document.documentElement;
  var KEY = 'kal_theme';
  var themeBtn = document.getElementById('theme');
  var menu = document.getElementById('menu');
  var mnav = document.getElementById('mnav');
  var header = document.querySelector('.hdr');

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
    }
    function openDrawer(){
      if (header){
        var h = Math.ceil(mnav.getBoundingClientRect().height);
        if (h > 0) header.style.setProperty('--drawer-h', (h + 1) + 'px');
        header.classList.add('open');
      }
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

  // Lightweight hover prefetch (capped, same-origin HTML only)
  var prefetched = new Set();
  document.addEventListener('pointerenter', function(ev){
    if (prefetched.size >= 20) return;
    var a = ev.target.closest ? ev.target.closest('a[href]') : null;
    if (!a || !a.href) return;
    try {
      var u = new URL(a.href, location.origin);
      if (u.origin !== location.origin) return;
      if (u.pathname === location.pathname) return;
      if (u.pathname.startsWith('/admin') || u.pathname.startsWith('/stagemaster') ||
          u.pathname.startsWith('/dashboard') || u.pathname.startsWith('/api')) return;
      if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(u.pathname)) return;
      if (prefetched.has(u.href)) return;
      prefetched.add(u.href);
      var link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = u.href;
      document.head.appendChild(link);
    } catch(e){}
  }, { capture: true, passive: true });

  if ('serviceWorker' in navigator){
    var rawBase = document.body.getAttribute('data-base') || '/';
    var swBase = rawBase.replace(/\/+$/, '');
    window.addEventListener('load', function(){
      navigator.serviceWorker.register(swBase + '/sw.js').catch(function(){});
    });
  }
})();
