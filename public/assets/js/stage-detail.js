(function(){
  'use strict';
  function apiBase(){
    if (location.port === '8000' || location.hostname === 'testserver') return '';
    var explicit = document.body.getAttribute('data-api');
    if (explicit != null) return explicit.replace(/\/+$/, '');
    return 'https://malakalolsavamapi.qd.je';
  }
  var liveEl = document.getElementById('stage-live');
  var schedEl = document.getElementById('stage-schedule');
  if (!liveEl && !schedEl) return;

  var BASE = apiBase();
  var stageName = (liveEl || schedEl).getAttribute('data-stage-name') || '';
  var normName = function(s){
    return String(s || '').toLowerCase().replace(/^stage\s*\d+\s*[-—:.]?\s*/i, '').trim();
  };
  var wantName = normName(stageName);

  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  }); }

  var venueId = null;
  var venueReady = false;

  function fetchVenues(){
    if (venueReady) return Promise.resolve(venueId);
    return fetch(BASE + '/api/v1/public/venues', { credentials: 'omit' })
      .then(function(r){ return r.json(); })
      .then(function(d){
        venueReady = true;
        var list = d.venues || [];
        for (var i = 0; i < list.length; i++){
          if (normName(list[i].name) === wantName){ venueId = list[i].id; break; }
        }
        return venueId;
      })
      .catch(function(){ venueReady = true; return null; });
  }

  // ── Live status ─────────────────────────────────────────
  function renderLive(d){
    var body = document.getElementById('stage-live-body');
    if (!body) return;

    if (!venueId){
      body.innerHTML = '<p class="text-muted sm" style="margin:0">This stage is not yet configured in the live backend. When the show is live, this section will display the current item and upcoming chest numbers.</p>';
      return;
    }

    var v = null;
    (d.venues || []).forEach(function(x){ if (x.id === venueId) v = x; });
    if (!v){
      body.innerHTML = '<p class="text-muted sm" style="margin:0">Stage configured but currently inactive.</p>';
      return;
    }

    var state = v.state || 'IDLE';
    var now = v.now;
    var upcoming = (v.upcoming || []);
    var html = '<div style="display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem">'
      + '<span class="badge-live"><span class="live-dot"></span>' + esc(state) + '</span>';
    if (v.progress && v.progress.total){
      html += '<span class="badge-gov" style="font-size:.7rem">' + v.progress.complete + ' / ' + v.progress.total + ' complete</span>';
    }
    html += '</div>';

    if (now){
      html += '<div class="stage-now-panel" style="background:var(--bg-alt);border-radius:var(--radius-inner);padding:1rem;margin-bottom:.75rem">'
        + '<small class="text-muted" style="text-transform:uppercase;letter-spacing:.05em;font-size:.7rem;font-weight:700">On stage now</small>'
        + '<div style="margin-top:.3rem;font-weight:700;font-size:1.05rem">' + esc(now.event || '—') + '</div>'
        + '<div class="text-muted sm" style="margin-top:.2rem">'
        + (now.roll ? '<strong>Chest #' + esc(now.roll) + '</strong> · ' : '')
        + esc(now.student_name || now.school || '—')
        + '</div></div>';
    } else {
      html += '<p class="text-muted sm" style="margin:0 0 .75rem">Stage is idle — no item on stage right now.</p>';
    }

    if (upcoming.length){
      html += '<small class="text-muted" style="text-transform:uppercase;letter-spacing:.05em;font-size:.7rem;font-weight:700">Up next</small>';
      html += '<ol style="margin:.4rem 0 0;padding-left:1.25rem">';
      for (var i = 0; i < upcoming.length; i++){
        var u = upcoming[i];
        html += '<li style="margin-bottom:.3rem">'
          + (u.roll ? '<strong>Chest #' + esc(u.roll) + '</strong> · ' : '')
          + esc(u.event || '—')
          + (u.student_name ? ' <span class="text-muted">— ' + esc(u.student_name) + '</span>' : '')
          + '</li>';
      }
      html += '</ol>';
    } else {
      html += '<p class="text-muted sm" style="margin:0">No items queued yet.</p>';
    }

    body.innerHTML = html;
  }

  function pollLive(){
    if (!document.body.contains(liveEl)) return false;
    fetch(BASE + '/api/v1/public/status', { credentials: 'omit' })
      .then(function(r){ return r.json(); })
      .then(renderLive)
      .catch(function(){
        var body = document.getElementById('stage-live-body');
        if (body) body.innerHTML = '<p class="text-muted sm" style="margin:0">Live updates start when the show goes live. This preview shows the static page.</p>';
      });
    return true;
  }

  // ── Schedule ────────────────────────────────────────────
  function renderSchedule(d){
    var body = document.getElementById('stage-schedule-body');
    if (!body) return;
    var events = (d.events || []).filter(function(e){
      return normName(e.venue || '') === wantName;
    });
    if (!events.length){
      body.innerHTML = '<p class="text-muted sm" style="margin:0">Competition schedule for this stage will be published closer to the event, or the stage is not yet configured in the backend.</p>';
      return;
    }
    var html = '<div style="overflow-x:auto"><table class="tbl"><thead><tr>'
      + '<th>Item</th><th>Code</th><th>Category</th><th>When</th></tr></thead><tbody>';
    events.forEach(function(e){
      html += '<tr><td>' + esc(e.title || '—') + '</td>'
        + '<td class="mono">' + esc(e.code || '') + '</td>'
        + '<td>' + esc(e.category || '—') + '</td>'
        + '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td></tr>';
    });
    html += '</tbody></table></div>';
    body.innerHTML = html;
  }

  function loadSchedule(){
    if (!document.body.contains(schedEl)) return;
    fetch(BASE + '/api/v1/public/schedule', { credentials: 'omit' })
      .then(function(r){ return r.json(); })
      .then(renderSchedule)
      .catch(function(){
        var body = document.getElementById('stage-schedule-body');
        if (body) body.innerHTML = '<p class="text-muted sm" style="margin:0">Schedule requires the festival backend. It will populate when the show is live.</p>';
      });
  }

  // ── Boot ────────────────────────────────────────────────
  var timer = null;
  var schedTimer = null;

  fetchVenues().then(function(){
    pollLive();
    loadSchedule();
    timer = setInterval(function(){
      if (!document.body.contains(liveEl)){ clearInterval(timer); timer = null; return; }
      pollLive();
    }, 5000);
    schedTimer = setInterval(function(){
      if (!document.body.contains(schedEl)){ clearInterval(schedTimer); schedTimer = null; return; }
      loadSchedule();
    }, 60000);
  });

  // SPA router cleanup hook
  var cleanupFn = function(){
    if (timer){ clearInterval(timer); timer = null; }
    if (schedTimer){ clearInterval(schedTimer); schedTimer = null; }
  };
  if (window.KalApp && typeof window.KalApp.onCleanup === 'function') {
    window.KalApp.onCleanup(cleanupFn);
  } else {
    window.__kalCleanup = cleanupFn;
  }
})();