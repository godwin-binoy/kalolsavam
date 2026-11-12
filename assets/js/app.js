(function(){
  'use strict';
  var html = document.documentElement;
  var KEY = 'kal_theme';
  var toggles = document.querySelectorAll('#theme, #theme-m');
  var menu = document.getElementById('menu');
  var mnav = document.getElementById('mnav');
  var CACHE_NAME = 'kal-page-cache-v11';

  // ── High-Performance Progress Indicator ─────────────────────────────
  var progressBar = document.createElement('div');
  progressBar.id = 'spa-progress';
  progressBar.style.cssText = 'position:fixed;top:0;left:0;height:2.5px;background:var(--brand);width:0;z-index:9999;transition:width .2s cubic-bezier(0.16,1,0.3,1),opacity .15s ease;opacity:0;pointer-events:none;';
  document.body.appendChild(progressBar);

  var progressTimer = null;
  function showProgress(){
    clearTimeout(progressTimer);
    progressTimer = setTimeout(function(){
      progressBar.style.opacity = '1';
      progressBar.style.width = '50%';
      setTimeout(function(){
        if (progressBar.style.opacity === '1') progressBar.style.width = '85%';
      }, 150);
    }, 70);
  }
  function hideProgress(){
    clearTimeout(progressTimer);
    progressBar.style.width = '100%';
    setTimeout(function(){
      progressBar.style.opacity = '0';
      setTimeout(function(){ progressBar.style.width = '0'; }, 200);
    }, 100);
  }

  // ── Theme Switcher ──────────────────────────────────────────────────
  toggles.forEach(function(btn){
    btn.addEventListener('click', function(){
      var dark = html.classList.toggle('dark');
      try { localStorage.setItem(KEY, dark ? 'dark' : 'light'); } catch(e){}
    });
  });

  // ── Mobile Drawer ───────────────────────────────────────────────────
  if (menu && mnav){
    var header = document.querySelector('.hdr');
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
      if (mnav.contains(ev.target)) return;
      if (menu.contains(ev.target)) return;
      closeDrawer();
    }, true);
    document.addEventListener('keydown', function(ev){
      if (ev.key === 'Escape' && mnav.classList.contains('open')) closeDrawer();
    });
  }

  // ── Aggressive Multi-Tier In-Memory + CacheStorage Engine ───────────
  var pageCache = new Map();
  var prefetchQueue = new Set();
  var currentController = null;
  var scrollPositions = new Map();

  function isPrefetchable(urlStr){
    try {
      var u = new URL(urlStr, location.origin);
      if (u.origin !== location.origin) return false;
      var path = u.pathname;
      if (path === location.pathname && u.search === location.search) return false;
      if (path.startsWith('/admin') || path.startsWith('/stagemaster') ||
          path.startsWith('/dashboard') || path.startsWith('/api') ||
          path.indexOf('/assets/') >= 0) return false;
      if (/\.(png|jpe?g|webp|gif|svg|pdf|zip|json|xml|txt)$/i.test(path)) return false;
      return true;
    } catch(e){
      return false;
    }
  }

  async function prefetch(urlStr, priority){
    if (!isPrefetchable(urlStr)) return;
    var normUrl = new URL(urlStr, location.origin).href;
    if (pageCache.has(normUrl) || prefetchQueue.has(normUrl)) return;

    prefetchQueue.add(normUrl);
    try {
      var res = await fetch(normUrl, {
        priority: priority || 'low',
        headers: { 'X-Purpose': 'preview' }
      });
      if (res.ok){
        var htmlText = await res.text();
        pageCache.set(normUrl, { html: htmlText, time: Date.now() });
        if ('caches' in window){
          caches.open(CACHE_NAME).then(function(c){
            c.put(normUrl, new Response(htmlText, {
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            }));
          }).catch(function(){});
        }
      }
    } catch(e){}
    finally {
      prefetchQueue.delete(normUrl);
    }
  }

  // ── Immediate Aggressive Route Warming ──────────────────────────────
  // Fires instantly the moment script executes, without waiting for hover or click
  // ── Purge Stale Caches on Boot ──────────────────────────────────────
  if ('caches' in window) {
    caches.keys().then(function(keys) {
      keys.forEach(function(k) {
        if (k !== 'kal-v19' && k !== 'kal-page-cache-v11') {
          caches.delete(k);
        }
      });
    });
  }

  function warmAggressively(){
    var rawBase = document.body.getAttribute('data-base') || '/';
    var base = rawBase.endsWith('/') ? rawBase : rawBase + '/';

    // 1. Core destination routes across festival modules
    var coreRoutes = [
      'venues', 'venues-live', 'venues-location', 'venues-find',
      'facilities', 'facilities-green-room', 'facilities-toilet',
      'transportation', 'transportation-bus', 'transportation-auto',
      'results', 'results-offstage', 'results-individual', 'results-group',
      'media', 'developers', 'help',
      'venues-stage/1', 'venues-stage/2', 'venues-stage/3',
      'venues-stage/4', 'venues-stage/5', 'venues-stage/6',
      'venues-stage/7', 'venues-stage/8', 'venues-stage/9'
    ];

    var targets = [];
    coreRoutes.forEach(function(r){
      targets.push(new URL(base + r, location.origin).href);
    });

    // 2. Discover every <a> link present in the active DOM
    document.querySelectorAll('a[href]').forEach(function(a){
      if (isPrefetchable(a.href)) targets.push(new URL(a.href, location.origin).href);
    });

    // Deduplicate
    var uniqueTargets = Array.from(new Set(targets)).filter(function(u){
      return !pageCache.has(u);
    });

    // Parallel background worker queue (batch concurrency of 4)
    var concurrency = 4;
    var index = 0;

    function runBatch(){
      while (index < uniqueTargets.length && concurrency > 0){
        var url = uniqueTargets[index++];
        concurrency--;
        prefetch(url, 'low').finally(function(){
          concurrency++;
          runBatch();
        });
      }
    }
    runBatch();
  }

  // Kick off aggressive prefetch immediately
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', warmAggressively);
  } else {
    warmAggressively();
      if (window.KalI18n && typeof window.KalI18n.apply === 'function') window.KalI18n.apply();
  }

  // Immediate priority boost on hover / touchstart
  document.addEventListener('pointerenter', function(ev){
    var a = ev.target.closest ? ev.target.closest('a[href]') : null;
    if (a && a.href && isPrefetchable(a.href)) prefetch(a.href, 'high');
  }, { capture: true, passive: true });

  document.addEventListener('touchstart', function(ev){
    var a = ev.target.closest ? ev.target.closest('a[href]') : null;
    if (a && a.href && isPrefetchable(a.href)) prefetch(a.href, 'high');
  }, { capture: true, passive: true });

  // ── Fast DOM Swap with View Transitions ─────────────────────────────
  async function fetchAndSwap(targetUrl, isBack){
    var normUrl = new URL(targetUrl, location.origin).href;
    showProgress();

    try {
      var htmlText = null;
      var cached = pageCache.get(normUrl);

      if (cached && cached.html){
        htmlText = cached.html;
      } else if ('caches' in window){
        var match = await caches.match(normUrl);
        if (match){
          htmlText = await match.text();
          pageCache.set(normUrl, { html: htmlText, time: Date.now() });
        }
      }

      if (!htmlText){
        var res = await fetch(normUrl, { signal: currentController ? currentController.signal : undefined });
        if (!res.ok) throw new Error('Fetch status ' + res.status);
        htmlText = await res.text();
        pageCache.set(normUrl, { html: htmlText, time: Date.now() });
      }

      var doc = new DOMParser().parseFromString(htmlText, 'text/html');
      var newMain = doc.getElementById('main');
      if (!newMain) {
        window.location.href = normUrl;
        return;
      }

      var titleEl = doc.querySelector('title');
      var newTitle = titleEl ? titleEl.textContent : document.title;
      var activeNav = doc.body.getAttribute('data-nav') || '';

      // Clean up previous listeners & polling intervals
      if (window.__kalCleanups && Array.isArray(window.__kalCleanups)){
        window.__kalCleanups.forEach(function(fn){ try { fn(); } catch(e){} });
      }
      if (typeof window.__kalCleanup === 'function'){
        try { window.__kalCleanup(); } catch(e){}
      }
      window.__kalCleanups = [];
      window.__kalCleanup = null;

      function renderNewPage(){
        document.title = newTitle;
        document.body.setAttribute('data-nav', activeNav);

        var mainEl = document.getElementById('main');
        mainEl.innerHTML = newMain.innerHTML;

        // Re-execute inline scripts
        mainEl.querySelectorAll('script').forEach(function(oldScript){
          var newScript = document.createElement('script');
          Array.from(oldScript.attributes).forEach(function(attr){
            newScript.setAttribute(attr.name, attr.value);
          });
          newScript.appendChild(document.createTextNode(oldScript.innerHTML));
          oldScript.parentNode.replaceChild(newScript, oldScript);
        });

        // Active state indicator
        document.querySelectorAll('.nav-link, .mnav a').forEach(function(navLink){
          if (navLink.getAttribute('data-active') === activeNav) navLink.classList.add('active');
          else navLink.classList.remove('active');
        });
      }

      if ('startViewTransition' in document){
        await document.startViewTransition(function(){
          renderNewPage();
        }).ready;
      } else {
        renderNewPage();
        if (window.KalI18n && typeof window.KalI18n.apply === 'function') window.KalI18n.apply();
      }

      var scrollPos = isBack && scrollPositions.has(normUrl) ? scrollPositions.get(normUrl) : 0;
      window.scrollTo({ top: scrollPos, left: 0, behavior: 'instant' });

      hideProgress();

      // Immediately warm any links newly mounted on the current page
      warmAggressively();

    } catch (err){
      hideProgress();
      if (err.name === 'AbortError') return;
      window.location.href = targetUrl;
    }
  }

  // ── Intercept Clicks for 0ms Instant Navigation ─────────────────────
  if (window.history.pushState){
    document.addEventListener('click', function(ev){
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button !== 0) return;
      var link = ev.target.closest('a');
      if (!link) return;
      var href = link.getAttribute('href');
      if (!href || href.startsWith('javascript:') || href.startsWith('http://') ||
          href.startsWith('https://') || href.startsWith('mailto:') || href.startsWith('tel:') ||
          link.target === '_blank' || link.hasAttribute('download')) return;

      if (!isPrefetchable(link.href)) return;

      if (href.startsWith('#')){
        ev.preventDefault();
        var target = document.querySelector(href);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }

      ev.preventDefault();
      if (mnav && mnav.classList.contains('open')){
        mnav.classList.remove('open');
        menu.setAttribute('aria-expanded', 'false');
      }

      scrollPositions.set(location.href, window.scrollY);

      var currentState = history.state || {};
      history.replaceState({ ...currentState, scroll: window.scrollY }, document.title, location.href);
      history.pushState({ url: link.href }, '', link.href);

      if (currentController) currentController.abort();
      currentController = new AbortController();

      fetchAndSwap(link.href, false);
    });

    window.addEventListener('popstate', function(){
      if (currentController) currentController.abort();
      currentController = new AbortController();
      fetchAndSwap(location.href, true);
    });
  }

  // ── Register Service Worker ─────────────────────────────────────────
  if ('serviceWorker' in navigator){
    var rawBase = document.body.getAttribute('data-base') || '/';
    var swBase = rawBase.replace(/\/+$/, '');
    window.addEventListener('load', function(){
      navigator.serviceWorker.register(swBase + '/sw.js').catch(function(){});
    });
  }
})();
