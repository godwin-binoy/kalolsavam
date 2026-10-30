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
    function setOpen(open) {
      menu.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', String(open));
    }
    btn.addEventListener('click', function () { setOpen(!menu.classList.contains('open')); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 768) setOpen(false); }, { passive: true });
  }

  function initPrefetch() {
    var root = window.location.pathname.indexOf('/pages/') !== -1 ? '../' : './';
    var idle = window.requestIdleCallback || function (cb) { setTimeout(cb, 300); };
    idle(function () {
      CONFIG.pages.forEach(function (p) {
        fetch(new URL(root + p, window.location.href).href, { credentials: 'same-origin' }).catch(function () {});
      });
    });
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
