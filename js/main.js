/* ==========================================================
   MALA SUB-DISTRICT KALOLSAVAM - SHARED BEHAVIORS
   Dark mode sync, mobile drawer, prefetch & scroll-reveal.

   NOTE: The dark-mode *bootstrap* (pre-paint theme application)
   is inlined in every page's <head> so it runs before the first
   frame — this file only wires up interactions afterwards.
   All handlers are registered once and bound defensively so
   missing elements on any page never throw.
   ========================================================== */

const DARK_KEY = 'kalolsavam_dark';
const CACHE_NAME = 'kalolsavam-ultra-cache-v3';

const SUN_SVG = '<svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path></svg>';
const MOON_SVG = '<svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path></svg>';

document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initMobileMenu();
  initPrefetch();
  initCardObservers();
});

/* ---------- Dark Mode (single delegated listener) ---------- */
function initDarkMode() {
  // The inline bootstrap already decided the theme on <html>; mirror it
  // onto <body> (some legacy selectors still target body.dark) and keep
  // both in sync on every toggle so back-forwards navigation never flashes.
  const isDark = document.documentElement.classList.contains('dark');
  document.body.classList.toggle('dark', isDark);

  // One listener on <body> handles both desktop + mobile toggles via delegation.
  document.body.addEventListener('click', (e) => {
    const toggle = e.target.closest('#dark-mode-toggle, #dark-mode-toggle-mobile');
    if (!toggle) return;

    const active = !document.documentElement.classList.contains('dark');
    document.documentElement.classList.toggle('dark', active);
    document.body.classList.toggle('dark', active);
    localStorage.setItem(DARK_KEY, String(active));
    updateToggleUI(active);
  });

  updateToggleUI(isDark);
}

function updateToggleUI(isDark) {
  document.querySelectorAll('#dark-mode-toggle, #dark-mode-toggle-mobile').forEach((btn) => {
    btn.innerHTML = isDark ? SUN_SVG : MOON_SVG;
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
const ALL_PAGES = [
  'index.html',
  'pages/venues.html',
  'pages/competitions.html',
  'pages/photos.html',
  'pages/facilities.html',
  'pages/help.html'
];

function warmUrl(href) {
  try {
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin) return null;
    return url.href.split('#')[0].split('?')[0];
  } catch (e) {
    return null;
  }
}

function prefetchHref(href) {
  const url = warmUrl(href);
  if (!url) return;
  fetch(url, { credentials: 'same-origin' }).catch(() => {});
}

function initPrefetch() {
  const root = window.location.pathname.includes('/pages/') ? '../' : './';
  const urls = ALL_PAGES.map((p) => root + p);

  const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300));
  idle(() => {
    if ('caches' in window) {
      caches.open(CACHE_NAME).then((cache) => {
        urls.forEach((url) => cache.add(url).catch(() => {}));
      }).catch(() => {
        urls.forEach((url) => prefetchHref(url));
      });
    } else {
      urls.forEach((url) => prefetchHref(url));
    }
  });

  // Opportunistic hover/focus warming — fires even if the idle pass raced.
  document.addEventListener('pointerover', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (a) prefetchHref(a.href);
  }, { passive: true });

  document.addEventListener('focusin', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (a) prefetchHref(a.href);
  }, { passive: true });
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
      const el = entry.target;
      el.style.transitionDelay = el.dataset.revealDelay || '0s';
      el.classList.add('revealed');
      observer.unobserve(el);
      // Drop the compositor hint shortly after the fade completes.
      setTimeout(() => { el.style.transitionDelay = ''; }, 400);
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  cards.forEach((card, index) => {
    card.classList.add('reveal-card');
    // Precompute stagger delay once (kept small so the page feels instant).
    card.dataset.revealDelay = `${Math.min(index * 0.03, 0.15)}s`;
    observer.observe(card);
  });
}
