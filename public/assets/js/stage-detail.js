(function(){
  'use strict';
  var K = window.Kal;
  var liveEl = document.getElementById('stage-live');
  var schedEl = document.getElementById('stage-schedule');
  if (!K || (!liveEl && !schedEl)) return;

  var BASE = K.apiBase();
  var srcEl = liveEl || schedEl;
  var wantSlug = srcEl.getAttribute('data-stage-slug') || '';
  var wantName = srcEl.getAttribute('data-stage-name') || '';

  function renderLive(d){
    var body = document.getElementById('stage-live-body');
    if (!body) return;
    var venues = (d && d.venues) || [];
    var v = null;
    for (var i = 0; i < venues.length; i++){
      if (K.matchStage(venues[i], wantSlug, wantName)){ v = venues[i]; break; }
    }

    if (!v){
      body.innerHTML = '<p class="text-muted sm" style="margin:0">This stage is not yet configured in the live backend. When the show is live, this section will display the current item and upcoming chest numbers.</p>';
      return;
    }

    var state = v.state || 'IDLE';
    var now = v.now;
    var upcoming = v.upcoming || [];
    var html = '<div style="display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem">'
      + '<span class="badge-live"><span class="live-dot"></span>' + K.esc(state) + '</span>';
    if (v.progress && v.progress.total){
      html += '<span class="badge-gov" style="font-size:.7rem">' + K.esc(v.progress.complete) + ' / ' + K.esc(v.progress.total) + ' complete</span>';
    }
    html += '</div>';

    if (now){
      html += '<div class="stage-now-panel" style="background:var(--bg-alt);border-radius:var(--radius-inner);padding:1rem;margin-bottom:.75rem">'
        + '<small class="text-muted" style="text-transform:uppercase;letter-spacing:.05em;font-size:.7rem;font-weight:700">On stage now</small>'
        + '<div style="margin-top:.3rem;font-weight:700;font-size:1.05rem">' + K.esc(now.event || '—') + '</div>'
        + '<div class="text-muted sm" style="margin-top:.2rem">'
        + (now.roll ? '<strong>Chest #' + K.esc(now.roll) + '</strong> · ' : '')
        + K.esc(now.student_name || now.school || '—')
        + '</div></div>';
    } else {
      html += '<p class="text-muted sm" style="margin:0 0 .75rem">Stage is idle — no item on stage right now.</p>';
    }

    if (upcoming.length){
      html += '<small class="text-muted" style="text-transform:uppercase;letter-spacing:.05em;font-size:.7rem;font-weight:700">Up next</small>';
      html += '<ol style="margin:.4rem 0 0;padding-left:1.25rem">';
      for (var j = 0; j < upcoming.length; j++){
        var u = upcoming[j];
        html += '<li style="margin-bottom:.3rem">'
          + (u.roll ? '<strong>Chest #' + K.esc(u.roll) + '</strong> · ' : '')
          + K.esc(u.event || '—')
          + (u.student_name ? ' <span class="text-muted">— ' + K.esc(u.student_name) + '</span>' : '')
          + '</li>';
      }
      html += '</ol>';
    } else {
      html += '<p class="text-muted sm" style="margin:0">No items queued yet.</p>';
    }

    body.innerHTML = html;
  }

  function renderSchedule(d){
    var body = document.getElementById('stage-schedule-body');
    if (!body) return;
    var normWant = K.normName(wantName);
    var events = ((d && d.events) || []).filter(function(e){
      if (wantSlug && e.venue_slug && String(e.venue_slug).toLowerCase() === wantSlug.toLowerCase()) return true;
      return K.normName(e.venue || '') === normWant;
    });
    if (!events.length){
      body.innerHTML = '<p class="text-muted sm" style="margin:0">Competition schedule for this stage has not been published yet.</p>';
      return;
    }
    var html = '<div style="overflow-x:auto"><table class="tbl"><thead><tr>'
      + '<th>Item</th><th>Code</th><th>Category</th><th>When</th></tr></thead><tbody>';
    events.forEach(function(e){
      html += '<tr><td>' + K.esc(e.title || '—') + '</td>'
        + '<td class="mono">' + K.esc(e.code || '') + '</td>'
        + '<td>' + K.esc(e.category || '—') + '</td>'
        + '<td>' + K.esc(e.day || '') + ' ' + K.esc(e.scheduled_time || '') + '</td></tr>';
    });
    html += '</tbody></table></div>';
    body.innerHTML = html;
  }

  if (liveEl){
    K.poll(function(){
      fetch(BASE + '/api/v1/public/status', { credentials: 'omit' })
        .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(renderLive)
        .catch(function(){
          var body = document.getElementById('stage-live-body');
          if (body) body.innerHTML = '<p class="text-muted sm" style="margin:0">Live updates unavailable right now.</p>';
        });
    }, 10000);
  }

  if (schedEl){
    K.poll(function(){
      fetch(BASE + '/api/v1/public/schedule', { credentials: 'omit' })
        .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(renderSchedule)
        .catch(function(){
          var body = document.getElementById('stage-schedule-body');
          if (body) body.innerHTML = '<p class="text-muted sm" style="margin:0">Unable to load schedule from server.</p>';
        });
    }, 60000);
  }
})();
