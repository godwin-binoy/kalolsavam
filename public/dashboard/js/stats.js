(function(){
  'use strict';
  var K = window.Kal;
  if (!K) return;
  var esc = K.esc, el = K.el;
  function fmtTime(ts){ try { return ts ? new Date(ts * 1000).toLocaleTimeString() : '—'; } catch(e){ return '—'; } }
  function num(v){ return (v == null || v === '') ? '0' : v; }
  function kpi(label, val, sub){
    return '<div class="card-base" style="padding:1rem 1.2rem"><div style="font-size:1.6rem;font-weight:800;color:var(--text-heading)">' + esc(num(val)) + '</div>' +
      '<div class="text-muted xs" style="text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-top:.2rem">' + esc(label) + '</div>' +
      (sub ? '<div class="text-muted xs" style="margin-top:.15rem">' + esc(sub) + '</div>' : '') + '</div>';
  }
  function render(d){
    var o = d.overall || {};
    el('kpi-grid').innerHTML = kpi('Active stages', num(o.active_venues) + ' / ' + num(o.venues)) + kpi('Running now', o.running_venues) +
      kpi('Events', o.events) + kpi('Participants', o.participants) + kpi('Item entries', o.entries) + kpi('Published photos', o.photos_published, 'Updated ' + fmtTime(d.updated_at));
    var rows = (d.per_venue || []).map(function(v){
      return '<tr><td>' + (v.active ? '<span class="badge-live">Active</span>' : '<span class="badge-gov">Inactive</span>') + '</td>' +
        '<td><strong>' + esc(v.name) + '</strong></td><td><span class="badge-gov">' + esc(v.active ? v.state : 'INACTIVE') + '</span></td>' +
        '<td>' + esc(v.current_item || '—') + '</td><td class="mono">' + esc(v.current_chest || '—') + '</td><td class="text-muted sm">' + esc(v.announcement || '—') + '</td></tr>';
    }).join('');
    el('venue-panel').innerHTML = '<h2 class="card-title">Live Stages Overview</h2><div style="overflow-x:auto"><table class="tbl">' +
      '<thead><tr><th>Active</th><th>Venue</th><th>Status</th><th>Current Item</th><th>Chest</th><th>Announcement</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="text-muted">No stages configured.</td></tr>') + '</tbody></table></div>';
  }
  K.poll(function(){
    K.fetchJSON('/api/v1/public/dashboard').then(render).catch(function(){
      el('kpi-grid').innerHTML = '<div class="card-base"><p class="text-muted" style="margin:0">Live statistics unavailable right now.</p></div>';
    });
  }, 15000);
})();
