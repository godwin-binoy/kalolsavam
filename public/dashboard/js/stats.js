(function(){
  'use strict';
  var K = window.Kal;
  if (!K) return;
  var esc = K.esc;
  var BASE = K.apiBase();

  function fmtTime(ts){
    if (!ts) return '—';
    try { return new Date(ts * 1000).toLocaleTimeString(); } catch(e){ return '—'; }
  }
  function pct(n, total){ return total ? Math.round((n / total) * 100) : 0; }
  function num(v){ return (v == null || v === '') ? '0' : v; }

  function kpiTile(label, value, sub){
    return '<div class="kpi">' +
      '<div class="kpi-value">' + esc(num(value)) + '</div>' +
      '<div class="kpi-label">' + esc(label) + '</div>' +
      (sub ? '<div class="kpi-sub">' + esc(sub) + '</div>' : '') +
    '</div>';
  }

  function renderKPIs(d){
    var o = d.overall || {};
    var progress = o.queue_items ? pct(o.queue_complete, o.queue_items) : 0;
    document.getElementById('kpi-grid').innerHTML =
      kpiTile('Active venues', num(o.active_venues) + ' / ' + num(o.venues)) +
      kpiTile('Events', o.events) +
      kpiTile('Participants', o.participants) +
      kpiTile('Queue items', o.queue_items, progress + '% complete') +
      kpiTile('On stage now', o.queue_onstage);
  }

  function renderVenues(d){
    var rows = (d.per_venue || []).map(function(v){
      var p = v.total ? pct(v.complete, v.total) : 0;
      var barColor = p >= 100 ? '#10B981' : p >= 50 ? '#D97706' : '#EAB308';
      return '<tr>' +
        '<td>' + (v.active ? '<span class="badge-live">Active</span>' : '<span class="badge-gov">Off</span>') + '</td>' +
        '<td>' + esc(v.name) + '</td>' +
        '<td class="num">' + v.total + '</td>' +
        '<td class="num">' + v.waiting + '</td>' +
        '<td class="num">' + v.onstage + '</td>' +
        '<td class="num">' + v.complete + '</td>' +
        '<td class="num">' + v.skipped + '</td>' +
        '<td style="width:150px">' +
          '<div style="height:6px;border-radius:999px;background:var(--bg-alt);overflow:hidden"><div style="height:100%;width:' + p + '%;background:' + barColor + '"></div></div>' +
          '<div class="text-muted xs" style="margin-top:.2rem">' + p + '%</div>' +
        '</td></tr>';
    }).join('');
    document.getElementById('venue-panel').innerHTML =
      '<h2 class="card-title">Venue Progress</h2>' +
      '<div style="overflow-x:auto"><table class="tbl">' +
        '<thead><tr><th>Status</th><th>Venue</th><th>Total</th><th>Waiting</th><th>On stage</th><th>Done</th><th>Skipped</th><th>Progress</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="8" class="text-muted">No venues configured.</td></tr>') + '</tbody>' +
      '</table></div>';
  }

  function renderSummary(d){
    var o = d.overall || {};
    var progress = o.queue_items ? pct(o.queue_complete, o.queue_items) : 0;
    document.getElementById('summary-panel').innerHTML =
      '<h2 class="card-title">Festival Summary</h2>' +
      '<dl class="stage-info">' +
        '<dt>Overall completion</dt><dd><strong>' + progress + '%</strong></dd>' +
        '<dt>Waiting in queue</dt><dd>' + esc(num(o.queue_waiting)) + '</dd>' +
        '<dt>Completed items</dt><dd>' + esc(num(o.queue_complete)) + '</dd>' +
        '<dt>Skipped items</dt><dd>' + esc(num(o.queue_skipped)) + '</dd>' +
        '<dt>Last updated</dt><dd>' + esc(fmtTime(d.updated_at)) + '</dd>' +
      '</dl>';
  }

  function renderRecentCompleted(d){
    var rows = (d.recent_completed || []).map(function(c){
      return '<tr>' +
        '<td class="sm">' + esc(fmtTime(c.completed_at)) + '</td>' +
        '<td class="mono sm">' + esc(c.event_code) + ' · ' + esc(c.event_title || '') + '</td>' +
        '<td class="sm">' + esc(c.venue_name || '—') + '</td>' +
      '</tr>';
    }).join('');
    document.getElementById('recent-completed-panel').innerHTML =
      '<h2 class="card-title">Recently Completed</h2>' +
      '<table class="tbl"><thead><tr><th>Time</th><th>Event</th><th>Venue</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="3" class="text-muted">No completions yet.</td></tr>') + '</tbody>' +
      '</table>';
  }

  function load(){
    fetch(BASE + '/api/v1/public/dashboard', { credentials: 'omit' })
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(d){
        renderKPIs(d);
        renderVenues(d);
        renderSummary(d);
        renderRecentCompleted(d);
      })
      .catch(function(){
        document.getElementById('kpi-grid').innerHTML =
          '<div class="card-base"><p class="text-muted" style="margin:0">Live statistics unavailable right now.</p></div>';
      });
  }

  K.poll(load, 30000);
})();
