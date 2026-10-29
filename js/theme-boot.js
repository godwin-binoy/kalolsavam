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
   ========================================================================== */
(function () {
  var h = document.documentElement, d, bg;
  try { d = localStorage.getItem('kalolsavam_dark') === 'true'; } catch (e) { d = false; }
  if (d) h.classList.add('dark');
  bg = d ? '#111412' : '#F8F6F0';
  h.style.backgroundColor = bg;
  h.style.setProperty('--boot-bg', bg);
})();
