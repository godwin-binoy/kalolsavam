/* ==========================================================
   MALA SUB-DISTRICT KALOLSAVAM - SHARED BEHAVIORS
   Dark mode toggle, mobile drawer, prefetch & scroll reveal.

   NOTE: The dark-mode *bootstrap* (pre-paint theme application)
   is inlined in every page's <head> so it runs before the first
   frame — this file only wires up interactions afterwards.
   All handlers are registered once and bound defensively so
   missing elements on any page never throw.
   ========================================================== */

const DARK_KEY = 'kalolsavam_dark';

/* Theme-toggle icons: one SVG per state, swapped by updateToggleUI().
   Fixed 16px size + .theme-toggle keeps button dimensions identical
   across states, so toggling never shifts the header layout. */
const TOGGLE_ICONS = {
  light: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>',
  dark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>'
};

document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initMobileMenu();
  initPrefetch();
  initCardObservers();
});

/* ---------- Dark Mode (single delegated listener) ---------- */
function initDarkMode() {
  // The inline bootstrap already decided the theme on <html>; all theme
  // selectors key off html.dark, so we only sync the toggle icons here.
  updateToggleUI(document.documentElement.classList.contains('dark'));

  // One listener on <body> handles both desktop + mobile toggles via delegation.
  document.body.addEventListener('click', (e) => {
    if (!e.target.closest('#dark-mode-toggle, #dark-mode-toggle-mobile')) return;

    const active = document.documentElement.classList.toggle('dark');
    localStorage.setItem(DARK_KEY, String(active));
    updateToggleUI(active);
  });
}

function updateToggleUI(isDark) {
  document.querySelectorAll('#dark-mode-toggle, #dark-mode-toggle-mobile').forEach((btn) => {
    btn.innerHTML = isDark ? TOGGLE_ICONS.dark : TOGGLE_ICONS.light;
    btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    btn.setAttribute('aria-pressed', String(isDark));
  });
}

/* ---------- Mobile Drawer ---------- */
function initMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  if (!btn || !menu) return;

  const closeMenu = () => {
    menu.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  };

  btn.setAttribute('aria-expanded', 'false');
  btn.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
  });

  menu.addEventListener('click', (e) => {
    if (e.target.closest('a')) closeMenu();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) closeMenu();
  }, { passive: true });
}

/* ---------- Prefetch sibling pages for instant navigation ----------
   Cross-document View Transitions animate the swap; what makes it FEEL
   instant is the next document already living in the HTTP cache.
   Strategy: warm all six pages during idle time, and re-warm a page the
   moment its nav link is hovered/focused/touched (zero-cost if cached). */
const SITE_PAGES = [
  'index.html',
  'pages/venues.html',
  'pages/competitions.html',
  'pages/photos.html',
  'pages/facilities.html',
  'pages/help.html'
];

/* Resolve any same-origin href to its absolute URL, minus #hash/?query noise. */
function warmUrl(href) {
  try {
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin) return null;
    url.hash = '';
    url.search = '';
    return url.href;
  } catch (e) {
    return null;
  }
}

function prefetchHref(href) {
  const url = warmUrl(href);
  if (url) fetch(url, { credentials: 'same-origin' }).catch(() => {});
}

function initPrefetch() {
  const root = window.location.pathname.includes('/pages/') ? '../' : './';
  const urls = SITE_PAGES.map((p) => root + p);

  // Warm everything once, off the critical path.
  const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300));
  idle(() => urls.forEach(prefetchHref));

  // Opportunistic hover/focus warming — fires even if the idle pass raced.
  const warmFromEvent = (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (a) prefetchHref(a.href);
  };
  document.addEventListener('pointerover', warmFromEvent, { passive: true });
  document.addEventListener('focusin', warmFromEvent, { passive: true });
}

/* ---------- Scroll Reveal (CSS-driven, GPU friendly) ---------- */
function initCardObservers() {
  // Respect reduced-motion users: cards are visible immediately.
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const cards = document.querySelectorAll('.card-base');
  if (!cards.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('revealed');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  cards.forEach((card, index) => {
    card.classList.add('reveal-card');
    // Stagger via a CSS custom property so JS never touches inline styles
    // or transition declarations (hover lift stays intact after reveal).
    card.style.setProperty('--reveal-delay', `${Math.min(index * 0.03, 0.15)}s`);
    observer.observe(card);
  });
}
