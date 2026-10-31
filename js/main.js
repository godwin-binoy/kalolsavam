(function () {
  'use strict';

  var CONFIG = {
    storageKey: 'kalolsavam_dark',
    darkClass: 'dark',
    toggleSelector: '#dark-mode-toggle, #dark-mode-toggle-mobile',
    menuButton: '#mobile-menu-btn',
    menuDrawer: '#mobile-menu',
    pages: ['index.html', 'pages/venues.html', 'pages/competitions.html', 'pages/photos.html', 'pages/facilities.html', 'pages/help.html'],
    labels: { light: 'Switch to Dark Mode', dark: 'Switch to Light Mode' }
  };

  var ICONS = {
    light: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>',
    dark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>'
  };

  var html = document.documentElement;

  function isDark() { return html.classList.contains(CONFIG.darkClass); }

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
    try { localStorage.setItem(CONFIG.storageKey, String(dark)); } catch (e) {}
    syncToggleUI();
    html.setAttribute('data-theme-anim', '');
    setTimeout(function () { html.removeAttribute('data-theme-anim'); }, 350);
  }

  function initTheme() {
    syncToggleUI();
    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest(CONFIG.toggleSelector);
      if (btn) { e.preventDefault(); toggleTheme(); }
    });
    window.addEventListener('storage', function (e) {
      if (e.key === CONFIG.storageKey) {
        html.classList.toggle(CONFIG.darkClass, e.newValue === 'true');
        syncToggleUI();
      }
    });
  }

  function initMobileMenu() {
    var btn = document.querySelector(CONFIG.menuButton);
    var menu = document.querySelector(CONFIG.menuDrawer);
    if (!btn || !menu) return;

    // Scrim element (tap-to-dismiss overlay behind the drawer)
    var scrim = document.createElement('div');
    scrim.className = 'drawer-scrim';
    scrim.setAttribute('aria-hidden', 'true');
    document.body.appendChild(scrim);

    function isOpen() { return menu.classList.contains('open'); }
    function setOpen(open) {
      menu.classList.toggle('open', open);
      scrim.classList.toggle('visible', open);
      document.body.classList.toggle('menu-open', open);
      btn.setAttribute('aria-expanded', String(open));
    }
    btn.addEventListener('click', function () { setOpen(!isOpen()); });
    scrim.addEventListener('click', function () { setOpen(false); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && isOpen()) setOpen(false); });
    // Close when a desktop-width nav becomes visible
    var mq = window.matchMedia('(min-width: 768px)');
    (mq.addEventListener ? mq.addEventListener('change', onBreak) : mq.addListener(onBreak));
    function onBreak(e) { if ((e.matches !== undefined ? e.matches : mq.matches) && isOpen()) setOpen(false); }
    // Safety: never leave body scroll-locked after navigating away mid-animation
    window.addEventListener('pageshow', function () { if (!isOpen()) setOpen(false); });
  }

  function initResultsLink() {
    // All "Results" links point at the official government portal. The static
    // build already embeds the correct URL (works with JS disabled too), and
    // target/rel are set in the HTML. When the live API is reachable we pick
    // up any admin-changed override from /api/public/meta — same-host only,
    // silently skipped on static hosting where the API isn't present.
    var links = document.querySelectorAll('[data-results-link]');
    if (!links.length) return;
    function apply(url) {
      var u;
      try { u = new URL(url); } catch (e) { return; }
      if (u.protocol !== 'https:' || !/(^|\.)kerala\.gov\.in$/.test(u.hostname)) return;
      links.forEach(function (a) {
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
      });
    }
    if (window.location.hostname === '' || window.location.hostname.endsWith('.github.io')) return;
    var meta = document.querySelector('meta[name="api-base"]');
    var base = meta ? meta.content.replace(/\/+$/, '') : '';
    var controller = ('AbortController' in window) ? new AbortController() : null;
    if (controller) setTimeout(function () { controller.abort(); }, 2500);
    fetch(base + '/api/public/meta', { credentials: 'same-origin', signal: controller ? controller.signal : undefined })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && j.results_url) apply(j.results_url); })
      .catch(function () {});
  }

  function initPrefetch() {
    var root = window.location.pathname.indexOf('/pages/') !== -1 ? '../' : './';
    var idle = window.requestIdleCallback || function (cb) { setTimeout(cb, 200); };
    idle(function () {
      CONFIG.pages.forEach(function (p) {
        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = new URL(root + p, window.location.href).href;
        document.head.appendChild(link);
      });
    });
  }

  function init() {
    initTheme();
    initMobileMenu();
    initResultsLink();
    initPrefetch();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
