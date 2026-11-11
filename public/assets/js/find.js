(function(){
  'use strict';
  function apiBase(){
    var b = document.body.getAttribute('data-base') || '/';
    return b.replace(/\/+$/, '');
  }
  var q = document.getElementById('q');
  var res = document.getElementById('results');
  var emp = document.getElementById('empty');
  if (!q || !res || !emp) return;

  var BASE = apiBase();
  var all = [];

  // Embedded festival program dataset for offline & preview availability
  var FALLBACK_EVENTS = [
    { code: "101", title: "Bharathanatyam (HS Girls)", venue: "Stage 1: Main Ground", day: "Day 1", scheduled_time: "09:30 AM", category: "HS General" },
    { code: "102", title: "Mohiniyattam (HSS Girls)", venue: "Stage 1: Main Ground", day: "Day 1", scheduled_time: "01:30 PM", category: "HSS General" },
    { code: "103", title: "Kuchipudi (HS Girls)", venue: "Stage 1: Main Ground", day: "Day 2", scheduled_time: "10:00 AM", category: "HS General" },
    { code: "201", title: "Light Music Vocal (HS Boys)", venue: "Stage 2: HS Hall", day: "Day 1", scheduled_time: "10:00 AM", category: "HS General" },
    { code: "202", title: "Classical Music Vocal (HSS)", venue: "Stage 2: HS Hall", day: "Day 1", scheduled_time: "02:00 PM", category: "HSS General" },
    { code: "203", title: "Mappilapattu (HS Girls)", venue: "Stage 2: HS Hall", day: "Day 2", scheduled_time: "09:30 AM", category: "HS General" },
    { code: "301", title: "Folk Dance (HS Boys)", venue: "Stage 3: GLPS Mala", day: "Day 1", scheduled_time: "10:30 AM", category: "HS General" },
    { code: "302", title: "Folk Dance (HSS Girls)", venue: "Stage 3: GLPS Mala", day: "Day 2", scheduled_time: "11:00 AM", category: "HSS General" },
    { code: "401", title: "Elocution Malayalam (HS)", venue: "Stage 4: HSS A1 B1 Classes", day: "Day 1", scheduled_time: "09:30 AM", category: "HS General" },
    { code: "402", title: "Elocution English (HSS)", venue: "Stage 4: HSS A1 B1 Classes", day: "Day 1", scheduled_time: "01:30 PM", category: "HSS General" },
    { code: "501", title: "Recitation Malayalam (HSS)", venue: "Stage 5: HSS Seminar Hall", day: "Day 1", scheduled_time: "10:00 AM", category: "HSS General" },
    { code: "502", title: "Recitation Sanskrit (HS)", venue: "Stage 5: HSS Seminar Hall", day: "Day 2", scheduled_time: "11:00 AM", category: "HS General" },
    { code: "601", title: "Oppana (HSS Girls)", venue: "Stage 6: Vyaapaara Bhavan", day: "Day 1", scheduled_time: "11:00 AM", category: "HSS General" },
    { code: "602", title: "Margamkali (HS Girls)", venue: "Stage 6: Vyaapaara Bhavan", day: "Day 2", scheduled_time: "01:30 PM", category: "HS General" },
    { code: "701", title: "Pencil Drawing (HS)", venue: "Stage 7: HSS 1st Floor Class", day: "Day 1", scheduled_time: "09:30 AM", category: "Off-Stage" },
    { code: "702", title: "Water Color Painting (HSS)", venue: "Stage 7: HSS 1st Floor Class", day: "Day 1", scheduled_time: "01:00 PM", category: "Off-Stage" },
    { code: "703", title: "Cartoon (HS)", venue: "Stage 7: HSS 1st Floor Class", day: "Day 2", scheduled_time: "10:00 AM", category: "Off-Stage" },
    { code: "801", title: "Clay Modeling (HS)", venue: "Stage 8: HS 9E Class", day: "Day 1", scheduled_time: "10:00 AM", category: "Off-Stage" },
    { code: "802", title: "Collage (HSS)", venue: "Stage 8: HS 9E Class", day: "Day 2", scheduled_time: "01:00 PM", category: "Off-Stage" },
    { code: "901", title: "Arabic Recitation (HS)", venue: "Stage 9: HS Arabic Class", day: "Day 1", scheduled_time: "10:00 AM", category: "HS General" },
    { code: "902", title: "Arabic Elocution (HSS)", venue: "Stage 9: HS Arabic Class", day: "Day 2", scheduled_time: "11:30 AM", category: "HSS General" }
  ];

  fetch(BASE + '/api/v1/public/schedule')
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){
      if (d && d.events && d.events.length) {
        all = d.events;
      } else {
        all = FALLBACK_EVENTS;
      }
      render('');
    })
    .catch(function(){
      all = FALLBACK_EVENTS;
      render('');
    });

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function render(filter){
    var f = (filter||'').trim().toLowerCase();
    var tokens = f.split(/\s+/).filter(Boolean);

    var matches = all.filter(function(e){
      if (!tokens.length) return true;
      var text = (String(e.code||'') + ' ' + String(e.title||'') + ' ' + String(e.venue||'') + ' ' + String(e.category||'')).toLowerCase();
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
              '<span class="fest-item-icon c-emerald"><span class="icn" style="--icon-url:url(\'' + BASE + 'assets/svg/map-pin.svg\')"></span></span>' +
              '<span><strong>Venue:</strong> ' + esc(e.venue || 'TBA') + '</span>' +
            '</span>' +
          '</div>' +
          '<div class="fest-action-item">' +
            '<span class="left">' +
              '<span class="fest-item-icon c-amber"><span class="icn" style="--icon-url:url(\'' + BASE + 'assets/svg/bolt.svg\')"></span></span>' +
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

  window.addEventListener('kal:langchange', function() {
    var qInput = document.getElementById('q');
    if (qInput && typeof render === 'function') {
      render(qInput.value);
    }
  });

})();
