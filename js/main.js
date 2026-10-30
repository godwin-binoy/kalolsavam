(function () {
  'use strict';

  var CONFIG = {
    storageKey: 'kalolsavam_dark',
    darkClass: 'dark',
    toggleSelector: '#dark-mode-toggle, #dark-mode-toggle-mobile',
    menuButton: '#mobile-menu-btn',
    menuDrawer: '#mobile-menu',
    revealTarget: '.card-base, .fest-card',
    reducedMotionQuery: '(prefers-reduced-motion: reduce)',
    pages: [
      'index.html',
      'pages/venues.html',
      'pages/competitions.html',
      'pages/photos.html',
      'pages/facilities.html',
      'pages/help.html'
    ],
    labels: {
      light: 'Switch to Dark Mode',
      dark: 'Switch to Light Mode'
    }
  };

  var ICONS = {
    light: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>',
    dark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>'
  };

  var html = document.documentElement;
  var prefersReducedMotion = window.matchMedia(CONFIG.reducedMotionQuery);

  function isDark() {
    return html.classList.contains(CONFIG.darkClass);
  }

  function syncToggleUI() {
    var dark = isDark();
    document.querySelectorAll(CONFIG.toggleSelector).forEach(function (btn) {
      btn.innerHTML = dark ? ICONS.dark : ICONS.light;
      btn.setAttribute('title', dark ? CONFIG.labels.dark : CONFIG.labels.light);
      btn.setAttribute('aria-pressed', String(dark));
    });
  }

  function toggleTheme() {
    var dark = html.classList.toggle(CONFIG.darkClass);
    try {
      localStorage.setItem(CONFIG.storageKey, String(dark));
    } catch (e) {}
    syncToggleUI();
    playThemeFade();
  }

  var fadeTimer = null;
  function playThemeFade() {
    if (prefersReducedMotion.matches) return;
    html.setAttribute('data-theme-anim', '');
    clearTimeout(fadeTimer);
    fadeTimer = setTimeout(function () {
      html.removeAttribute('data-theme-anim');
    }, 350);
  }

  function initTheme() {
    syncToggleUI();
    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest(CONFIG.toggleSelector);
      if (btn) {
        e.preventDefault();
        toggleTheme();
      }
    });

    window.addEventListener('storage', function (e) {
      if (e.key !== CONFIG.storageKey) return;
      var dark = e.newValue === 'true';
      html.classList.toggle(CONFIG.darkClass, dark);
      syncToggleUI();
    });
  }

  function initMobileMenu() {
    var btn = document.querySelector(CONFIG.menuButton);
    var menu = document.querySelector(CONFIG.menuDrawer);
    if (!btn || !menu) return;

    function setOpen(open) {
      menu.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', String(open));
    }

    btn.addEventListener('click', function () {
      setOpen(!menu.classList.contains('open'));
    });

    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 768) setOpen(false);
    }, { passive: true });
  }

  function warmUrl(href) {
    try {
      var url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return null;
      url.hash = '';
      url.search = '';
      return url.href;
    } catch (e) {
      return null;
    }
  }

  function prefetchHref(href) {
    var url = warmUrl(href);
    if (url) fetch(url, { credentials: 'same-origin' }).catch(function () {});
  }

  function initPrefetch() {
    var root = window.location.pathname.indexOf('/pages/') !== -1 ? '../' : './';
    var idle = window.requestIdleCallback || function (cb) { setTimeout(cb, 300); };
    idle(function () {
      CONFIG.pages.forEach(function (p) { prefetchHref(root + p); });
    });

    function warmFromEvent(e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (a) prefetchHref(a.href);
    }
    document.addEventListener('pointerover', warmFromEvent, { passive: true });
    document.addEventListener('focusin', warmFromEvent, { passive: true });
  }

  function init() {
    initTheme();
    initMobileMenu();
    initPrefetch();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
