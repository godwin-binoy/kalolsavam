/* ==========================================================================
   KALOLSAVAM THEME BOOTSTRAP — canonical source (inlined at build time)
   --------------------------------------------------------------------------
   tools/build.py reads THIS file, strips comments, and inlines the IIFE into
   every page's <head>, so exactly one copy of this logic exists in the repo.
   It must run synchronously BEFORE first paint: never add defer/async to the
   inline tag and never move it below the stylesheet links.

   Contract with the rest of the codebase:
   1. Theme state lives ONLY on <html class="dark">. No body mirror, no
      data-attribute duplication — CSS (`html.dark …`) and JS both read it.
   2. Storage key "kalolsavam_dark" ("true"/"false") is the persistence
      layer; js/main.js writes it, this snippet reads it. One key, one format.
   3. --boot-bg + html background-color are painted here before CSS loads,
      so frame #1 (and View-Transition snapshots) already match the theme.
      Colors below MUST stay in sync with --color-body-bg in css/variables.css.
   4. "lo-power" marks weak devices (few cores / little RAM / Save-Data on).
      css/base.css zeroes backdrop-blur for that class. The verdict is cached
      under "kalolsavam_lp" so repeat visits decide with zero cost and the
      tier never flips mid-session (no layout jumps between pages).
   ========================================================================== */
(function () {
  var h = document.documentElement, d, bg, lp;
  try { d = localStorage.getItem('kalolsavam_dark') === 'true'; } catch (e) { d = false; }
  if (d) h.classList.add('dark');
  bg = d ? '#111412' : '#F8F6F0';
  h.style.backgroundColor = bg;
  h.style.setProperty('--boot-bg', bg);

  /* Low-end device detection: a handful of cheap property reads (<0.1ms),
     executed at most once ever thanks to the cache above. */
  try { lp = localStorage.getItem('kalolsavam_lp'); } catch (e) { lp = null; }
  if (lp !== '0' && lp !== '1') {
    var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    lp = ((navigator.hardwareConcurrency || 8) <= 2) ||
         ((navigator.deviceMemory || 8) <= 2) ||
         (c && c.saveData === true) ? '1' : '0';
    try { localStorage.setItem('kalolsavam_lp', lp); } catch (e) {}
  }
  if (lp === '1') h.classList.add('lo-power');
})();
