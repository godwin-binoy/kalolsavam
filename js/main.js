/* ==========================================================================
   MALA SUB-DISTRICT KALOLSAVAM — SHARED INTERACTIONS (single JS entry)
   --------------------------------------------------------------------------
   Loaded with `defer` on every page. The pre-paint theme bootstrap is NOT
   here: it lives in js/theme-boot.js and is inlined into each <head> by
   tools/build.py, so the saved theme is applied before the first frame.

   Invariants this file relies on (enforced by the build template):
   * Theme state = <html class="dark"> ONLY. We read/toggle that class and
     nothing else — no body mirror, no second source of truth.
   * Toggle buttons (#dark-mode-toggle, #dark-mode-toggle-mobile) ship empty
     in HTML; we inject fixed-size SVGs so icon swaps never shift layout.
   * Pages are generated from tools/build.py — element IDs are guaranteed to
     exist on every page, but handlers stay defensive anyway.
   ========================================================================== */
(function () {
  'use strict';

  /* ---------- Global config: one place for keys, selectors, copy ---------- */
  var CONFIG = {
    storageKey: 'kalolsavam_dark',
    darkClass: 'dark',
    toggleSelector: '#dark-mode-toggle, #dark-mode-toggle-mobile',
    menuButton: '#mobile-menu-btn',
    menuDrawer: '#mobile-menu',
    revealTarget: '.card-base',
    reducedMotionQuery: '(prefers-reduced-motion: reduce)',
    /* Relative to site root; resolved per page depth at runtime. */
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

  /* Fixed 16px stroke icons — identical box in both states (no emoji). */
  var ICONS = {
    light: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>',
    dark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>'
  };

  var html = document.documentElement;
  var prefersReducedMotion = window.matchMedia(CONFIG.reducedMotionQuery);

  /* ---------- Theme (single delegated listener, single source of truth) -- */
  function isDark() {
    return html.classList.contains(CONFIG.darkClass);
  }

  /* Paint the current state onto every toggle button. Written as a pure
     function of `isDark()` so it can be re-run after any DOM change
     (e.g. the mobile drawer cloning its controls) and always converge. */
  function syncToggleUI() {
    var dark = isDark();
    document.querySelectorAll(CONFIG.toggleSelector).forEach(function (btn) {
      btn.innerHTML = dark ? ICONS.dark : ICONS.light;
      btn.setAttribute('title', dark ? CONFIG.labels.dark : CONFIG.labels.light);
      btn.setAttribute('aria-pressed', String(dark));
    });
  }

  /* The ONLY place the theme changes: toggle <html class="dark"> once,
     persist it, then re-sync icon + labels + ARIA from the new state.
     Note: we never mutate aria-checked here — these are <button>s, so
     aria-pressed is the correct live state attribute (and toggling
     aria-checked too caused screen readers to announce stale states). */
  function toggleTheme() {
    var dark = html.classList.toggle(CONFIG.darkClass);
    try {
      localStorage.setItem(CONFIG.storageKey, String(dark));
    } catch (e) { /* storage blocked (private mode): theme still applies now */ }
    syncToggleUI();
    playThemeFade();
  }

  /* Scoped theme cross-fade: enable the CSS rule via <html data-theme-anim>
     for one fade cycle, then remove it. Transitions therefore run ONLY on
     explicit toggles — page loads, navigation and View Transitions stay
     instant instead of every element fading on first paint. */
  var fadeTimer = null;
  function playThemeFade() {
    if (prefersReducedMotion.matches) return; // CSS already zeroes durations
    html.setAttribute('data-theme-anim', '');
    clearTimeout(fadeTimer);
    fadeTimer = setTimeout(function () {
      html.removeAttribute('data-theme-anim');
    }, 350); // matches --theme-fade (0.3s) + safety margin in variables.css
  }

  function initTheme() {
    // Bootstrap already set <html class="dark"> pre-paint; only sync icons.
    syncToggleUI();

    /* One DELEGATED click handler on <body> covers every toggle — desktop,
       mobile drawer, and any future copy — with zero per-element wiring.
       Delegation is what keeps the two buttons in lockstep: both resolve
       to the same toggleTheme(), which reads/writes exactly one class. */
    document.body.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest(CONFIG.toggleSelector);
      if (btn) {
        e.preventDefault(); // buttons are type=button already; safe no-op guard
        toggleTheme();
      }
    });

    /* Keep multiple tabs in sync: when another tab flips the theme, adopt
       its state and repaint this page's toggles (no storage write needed). */
    window.addEventListener('storage', function (e) {
      if (e.key !== CONFIG.storageKey) return;
      var dark = e.newValue === 'true';
      html.classList.toggle(CONFIG.darkClass, dark);
      syncToggleUI();
    });
  }

  /* ---------- Mobile drawer ---------- */
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

    // Close after tapping any link inside the drawer.
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 768) setOpen(false);
    }, { passive: true });
  }

  /* ---------- Prefetch: instant cross-page navigation ----------
     Cross-document View Transitions animate the swap; what makes it FEEL
     instant is the next document already living in the HTTP cache.
     Strategy: warm all pages during idle time, and re-warm a page the
     moment its link is hovered/focused (zero-cost if already cached). */
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

    // Opportunistic hover/focus warming — fires even if the idle pass raced.
    function warmFromEvent(e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (a) prefetchHref(a.href);
    }
    document.addEventListener('pointerover', warmFromEvent, { passive: true });
    document.addEventListener('focusin', warmFromEvent, { passive: true });
  }

  /* ---------- Scroll reveal (CSS-driven, GPU friendly) ---------- */
  function initReveal() {
    if (prefersReducedMotion.matches) return; // cards stay visible immediately

    var cards = document.querySelectorAll(CONFIG.revealTarget);
    if (!cards.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

    Array.prototype.forEach.call(cards, function (card, index) {
      card.classList.add('reveal-card');
      // Stagger via a CSS custom property so JS never touches inline styles
      // or transition declarations (hover lift stays intact after reveal).
      card.style.setProperty('--reveal-delay', Math.min(index * 0.03, 0.15) + 's');
      observer.observe(card);
    });
  }

  /* ---------- Boot ---------- */
  function init() {
    initTheme();
    initMobileMenu();
    initPrefetch();
    initReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init(); // defer scripts run after parsing, but keep this robust anyway
  }
})();
