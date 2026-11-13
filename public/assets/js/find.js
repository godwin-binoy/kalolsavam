(function(){
  'use strict';
  var K = window.Kal;
  var rawBase = document.body.getAttribute('data-base') || '/';
  var ASSET_BASE = rawBase.endsWith('/') ? rawBase : rawBase + '/';
  var q = document.getElementById('q');
  var res = document.getElementById('results');
  var emp = document.getElementById('empty');
  if (!K || !q || !res || !emp) return;

  var BASE = K.apiBase();
  var all = [];
  var loaded = false;
  var loadError = false;

  fetch(BASE + '/api/v1/public/schedule', { credentials: 'omit' })
    .then(function(r){
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .then(function(d){
      loaded = true;
      all = (d && Array.isArray(d.events)) ? d.events : [];
      render(q.value);
    })
    .catch(function(){
      loaded = true;
      loadError = true;
      all = [];
      render(q.value);
    });

  function render(filter){
    if (!loaded) return;
    if (loadError){
      res.innerHTML = '';
      emp.hidden = false;
      emp.textContent = 'Unable to load the schedule right now. Please check your connection and try again.';
      return;
    }
    if (!all.length){
      res.innerHTML = '';
      emp.hidden = false;
      emp.textContent = 'Official competition schedule has not been published yet.';
      return;
    }

    var f = (filter || '').trim().toLowerCase();
    var tokens = f.split(/\s+/).filter(Boolean);
    var matches = all.filter(function(e){
      if (!tokens.length) return true;
      var text = (String(e.code || '') + ' ' + String(e.title || '') + ' ' + String(e.venue || '') + ' ' + String(e.category || '')).toLowerCase();
      return tokens.every(function(t){ return text.indexOf(t) >= 0; });
    });

    emp.hidden = matches.length > 0;
    emp.textContent = 'No matching competition items found. Try searching by number (e.g. 101) or item name (e.g. Oppana).';

    res.innerHTML = matches.slice(0, 60).map(function(e){
      return '<div class="fest-card">' +
        '<div class="fest-header banner-blue">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.2rem">' +
            '<span style="font-size:.75rem;padding:.2rem .6rem;background:rgba(255,255,255,.2);border-radius:999px;font-weight:700">Item #' + K.esc(e.code) + '</span>' +
            '<span style="font-size:.75rem;opacity:.9">' + K.esc(e.category || '') + '</span>' +
          '</div>' +
          '<h3 class="fest-title" style="font-size:1.15rem">' + K.esc(e.title || '') + '</h3>' +
        '</div>' +
        '<div class="fest-body">' +
          '<div class="fest-action-item">' +
            '<span class="left">' +
              '<span class="fest-item-icon c-emerald"><span class="icn" style="--icon-url:url(\'' + ASSET_BASE + 'assets/svg/map-pin.svg\')"></span></span>' +
              '<span><strong>Venue:</strong> ' + K.esc(e.venue || 'TBA') + '</span>' +
            '</span>' +
          '</div>' +
          '<div class="fest-action-item">' +
            '<span class="left">' +
              '<span class="fest-item-icon c-amber"><span class="icn" style="--icon-url:url(\'' + ASSET_BASE + 'assets/svg/bolt.svg\')"></span></span>' +
              '<span><strong>Schedule:</strong> ' + K.esc(e.day || '') + ' · ' + K.esc(e.scheduled_time || '') + '</span>' +
            '</span>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  var debounceTimer = null;
  q.addEventListener('input', function(){
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function(){ render(q.value); }, 120);
  });
})();
