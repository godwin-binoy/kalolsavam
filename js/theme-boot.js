(function () {
  var h = document.documentElement, d, bg;
  try { d = localStorage.getItem('kalolsavam_dark') === 'true'; } catch (e) { d = false; }
  if (d) h.classList.add('dark');
  bg = d ? '#0F1311' : '#F8F6F0';
  h.style.backgroundColor = bg;
  h.style.setProperty('--boot-bg', bg);
  /* manual dark choice must win over the media-query meta pair */
  if (d) { var m = document.querySelector('meta[name="theme-color"][media*="light"]'); if (m) m.media = '(prefers-color-scheme: dark)'; }
  /* Keep the browser chrome (status bar) matched to the page theme */
  function setTC(c) {
    var m = document.querySelector('meta[name="theme-color"]');
    if (!m) { m = document.createElement('meta'); m.name = 'theme-color'; document.head.appendChild(m); }
    m.content = c;
  }
  setTC(bg);
  window.__setThemeColor = setTC;
})();
