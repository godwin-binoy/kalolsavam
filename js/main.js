(function () {
  'use strict';

  var html = document.documentElement;
  var DARK = 'dark', KEY = 'kalolsavam_dark';
  var ICONS = {
    light: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>',
    dark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>'
  };

  function isDark() { return html.classList.contains(DARK); }

  function syncToggles() {
    var dark = isDark();
    document.querySelectorAll('.theme-toggle').forEach(function (b) {
      b.innerHTML = dark ? ICONS.dark : ICONS.light;
      b.setAttribute('aria-pressed', String(dark));
      b.setAttribute('aria-label', dark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    });
    if (window.__setThemeColor) window.__setThemeColor(dark ? '#0F1311' : '#F8F6F0');
  }

  // Theme — boot script already applied the saved class; here we only wire UI.
  syncToggles();
  document.body.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.theme-toggle');
    if (!btn) return;
    e.preventDefault();
    html.classList.toggle(DARK);
    try { localStorage.setItem(KEY, String(isDark())); } catch (err) {}
    syncToggles();
    html.setAttribute('data-theme-anim', '');
    setTimeout(function () { html.removeAttribute('data-theme-anim'); }, 350);
  });
  window.addEventListener('storage', function (e) {           // cross-tab sync
    if (e.key === KEY) { html.classList.toggle(DARK, e.newValue === 'true'); syncToggles(); }
  });

  // Drawer — fixed overlay panel; page stays exactly where it is.
  var menuBtn = document.getElementById('mobile-menu-btn');
  var menu = document.getElementById('mobile-menu');
  if (menuBtn && menu) {
    var scrim = document.createElement('div');
    scrim.className = 'drawer-scrim';
    scrim.setAttribute('aria-hidden', 'true');
    document.body.appendChild(scrim);

    function setMenu(open) {
      menu.classList.toggle('open', open);
      scrim.classList.toggle('visible', open);
      document.body.classList.toggle('menu-open', open);
      menuBtn.setAttribute('aria-expanded', String(open));
    }
    function measureHeader() {
      var h = document.querySelector('.site-header');
      if (h) html.style.setProperty('--header-h', h.offsetHeight + 'px');
    }
    measureHeader();
    addEventListener('resize', measureHeader, { passive: true });
    menuBtn.addEventListener('click', function () { setMenu(!menu.classList.contains('open')); });
    scrim.addEventListener('click', function () { setMenu(false); });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
    var mq = matchMedia('(min-width: 768px)');
    (mq.addEventListener || mq.addListener).call(mq, 'change', function (e) { if (e.matches) setMenu(false); });
    addEventListener('pageshow', function () { setMenu(false); measureHeader(); }); // never stuck after back-nav
  }

  // Results links → official government portal (static URL works without JS;
  // when the API is reachable we pick up any admin-changed override).
  var govUrl = 'https://kalolsavam.kerala.gov.in/';
  function applyResults(url) {
    var u; try { u = new URL(url); } catch (e) { return; }
    if (u.protocol !== 'https:' || !/(^|\.)kerala\.gov\.in$/.test(u.hostname)) return;
    document.querySelectorAll('[data-results-link]').forEach(function (a) { a.href = url; });
  }
  var meta = document.querySelector('meta[name="api-base"]');
  if (meta && meta.content) {
    var ac = typeof AbortController !== 'undefined' ? new AbortController() : null;
    if (ac) setTimeout(function () { ac.abort(); }, 2500);
    fetch(meta.content.replace(/\/+$/, '') + '/api/public/meta',
          { credentials: 'same-origin', signal: ac && ac.signal })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && j.results_url) applyResults(j.results_url); })
      .catch(function () {});   // offline / static hosting → keep the built-in gov URL
  } else {
    applyResults(govUrl);
  }
})();
