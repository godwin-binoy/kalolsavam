(function(){
  'use strict';
  var rawBase = document.body.getAttribute('data-base') || '/';
  var ASSET_BASE = rawBase.endsWith('/') ? rawBase : rawBase + '/';
  function resolveApiBase(){
    if (location.port === '8000' || location.hostname === 'testserver') return '';
    var explicit = document.body.getAttribute('data-api');
    if (explicit != null) return explicit.replace(/\/+$/, '');
    return 'https://malakalolsavamapi.qd.je';
  }
  var API_BASE = resolveApiBase();

  var q = document.getElementById('q');
  var res = document.getElementById('results');
  var emp = document.getElementById('empty');
  if (!q || !res || !emp) return;

  var all = [];

  // Embedded festival program dataset for offline & preview availability
  var FALLBACK_EVENTS = [
    { code: "101", title: "Bharathanatyam (HS Girls)", venue: "Stage 1: Main Ground", day: "Day 1", scheduled_time: "09:30 AM", category: "HS General" },
    { code: "201", title: "Light Music Vocal (HS Boys)", venue: "Stage 2: HS Hall", day: "Day 1", scheduled_time: "10:00 AM", category: "HS General" },
    { code: "301", title: "Folk Dance (HS Boys)", venue: "Stage 3: GLPS Mala", day: "Day 1", scheduled_time: "10:30 AM", category: "HS General" },
    { code: "401", title: "Elocution Malayalam (HS)", venue: "Stage 4: HSS A1 B1", day: "Day 1", scheduled_time: "09:30 AM", category: "HS General" },
    { code: "601", title: "Oppana (HSS Girls)", venue: "Stage 6: Vyaapaara Bhavan", day: "Day 1", scheduled_time: "11:00 AM", category: "HSS General" },
    { code: "701", title: "Pencil Drawing (HS)", venue: "Stage 7: HSS 1st Floor", day: "Day 1", scheduled_time: "09:30 AM", category: "Off-Stage" }
  ];

  fetch(API_BASE + '/api/v1/public/schedule')
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){
      all = (d && d.events && d.events.length) ? d.events : FALLBACK_EVENTS;
      render('');
    })
    .catch(function(){
      all = FALLBACK_EVENTS;
      render('');
    });

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function render(filter){
    if (!document.body.contains(res)) return;
    var f = (filter || '').trim().toLowerCase();
    var tokens = f.split(/\s+/).filter(Boolean);

    var matches = all.filter(function(e){
      if (!tokens.length) return true;
      var text = (String(e.code || '') + ' ' + String(e.title || '') + ' ' + String(e.venue || '') + ' ' + String(e.category || '')).toLowerCase();
      return tokens.every(function(t){ return text.indexOf(t) >= 0; });
    });

    emp.hidden = matches.length > 0;
    emp.textContent = 'No matching competition items found. Try searching by number (e.g. 101) or item name (e.g. Oppana).';

    res.innerHTML = matches.slice(0, 40).map(function(e){
      return '<div class="fest-card">' +
        '<div class="fest-header banner-blue">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.2rem">' +
            '<span style="font-size:.75rem;padding:.2rem .6rem;background:rgba(255,255,255,.2);border-radius:999px;font-weight:700">Item #' + esc(e.code) + '</span>' +
            '<span style="font-size:.75rem;opacity:.9">' + esc(e.category || '') + '</span>' +
          '</div>' +
          '<h3 class="fest-title" style="font-size:1.15rem">' + esc(e.title || '') + '</h3>' +
        '</div>' +
        '<div class="fest-body">' +
          '<div class="fest-action-item">' +
            '<span class="left">' +
              '<span class="fest-item-icon c-emerald"><span class="icn" style="--icon-url:url(\'' + ASSET_BASE + 'assets/svg/map-pin.svg\')"></span></span>' +
              '<span><strong>Venue:</strong> ' + esc(e.venue || 'TBA') + '</span>' +
            '</span>' +
          '</div>' +
          '<div class="fest-action-item">' +
            '<span class="left">' +
              '<span class="fest-item-icon c-amber"><span class="icn" style="--icon-url:url(\'' + ASSET_BASE + 'assets/svg/bolt.svg\')"></span></span>' +
              '<span><strong>Schedule:</strong> ' + esc(e.day || '') + ' · ' + esc(e.scheduled_time || '') + '</span>' +
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

  function onLangChange(){
    var qInput = document.getElementById('q');
    if (qInput && document.body.contains(qInput)) render(qInput.value);
  }
  window.addEventListener('kal:langchange', onLangChange);

  if (window.KalApp && typeof window.KalApp.onCleanup === 'function'){
    window.KalApp.onCleanup(function(){
      clearTimeout(debounceTimer);
      window.removeEventListener('kal:langchange', onLangChange);
    });
  }
})();
