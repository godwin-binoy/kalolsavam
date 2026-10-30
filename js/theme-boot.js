(function () {
  var h = document.documentElement, d, bg;
  try { d = localStorage.getItem('kalolsavam_dark') === 'true'; } catch (e) { d = false; }
  if (d) h.classList.add('dark');
  bg = d ? '#0F1311' : '#F8F6F0';
  h.style.backgroundColor = bg;
  h.style.setProperty('--boot-bg', bg);
})();
