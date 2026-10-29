/* ==========================================================
   KALOLSAVAM - THEME BOOTSTRAP (single source of truth)
   ------------------------------------------------------------
   The ACTUAL bootstrap is inlined in every page's <head> (see
   index.html / pages/*.html) so it executes BEFORE first paint
   without costing an extra network round-trip. This file keeps a
   readable, commented copy of that exact logic for maintenance.

   It solves the dark-mode white flash on navigation:
   1. Reads localStorage synchronously and puts .dark on <html>
      before any content renders (all theme tokens/selectors key
      off html.dark — body never needs a mirror class).
   2. Paints the theme-correct background color directly on <html>
      (and via --boot-bg into the html::before fixed backdrop), so
      frame #1 — and every View-Transition snapshot taken before
      stylesheets arrive — is already dark. No light->dark flip.

   KEEP IN SYNC with the inline snippet in each HTML head.
   ========================================================== */
(function () {
  var html = document.documentElement, dark, bg;
  try {
    dark = localStorage.getItem('kalolsavam_dark') === 'true';
  } catch (e) {
    dark = false; // private mode / blocked storage: fall back to light
  }
  if (dark) html.classList.add('dark');
  bg = dark ? '#111412' : '#F8F6F0';
  html.style.backgroundColor = bg;          // canvas color (overscroll + VT snapshots)
  html.style.setProperty('--boot-bg', bg);  // consumed by css/base.css backdrop
})();
