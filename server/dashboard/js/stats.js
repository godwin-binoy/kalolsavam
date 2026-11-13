(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var REFRESH_MS = 30000;
  var timer = null;
  var loading = false;

  function fmtBytes(n){
    if (!n || n < 0) return '—';
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n/1024).toFixed(1) + ' KB';
    if (n < 1073741824) return (n/1048576).toFixed(2) + ' MB';
    return (n/1073741824).toFixed(2) + ' GB';
  }
  function fmtTime(ts){
    if (!ts) return '—';
    try { return new Date(ts * 1000).toLocaleTimeString(); } catch(e){ return '—'; }
  }
  function pct(n, total){ return total ? Math.round((n/total)*100) : 0; }
  function num(v){ return (v == null || v === '') ? '0' : v; }

  function kpiTile(label, value, sub){
    return '<div class="kpi">' +
      '<div class="kpi-value">' + esc(num(value)) + '</div>' +
      '<div class="kpi-label">' + esc(label) + '</div>' +
      (sub ? '<div class="kpi-sub">' + esc(sub) + '</div>' : '') +
    '</div>';
  }

  function renderKPIs(d){
    var o = d.overall;
    var progress = o.queue_items ? pct(o.queue_complete, o.queue_items) : 0;
    document.getElementById('kpi-grid').innerHTML =
      kpiTile('Active venues', o.active_venues + ' / ' + o.venues) +
      kpiTile('Events', o.events) +
      kpiTile('Participants', o.participants) +
      kpiTile('Queue items', o.queue_items, progress + '% complete') +
      kpiTile('On stage now', o.queue_onstage) +
      kpiTile('Score entries', o.scores_entered);
  }

  function renderVenues(d){
    var rows = d.per_venue.map(function(v){
      var p = v.total ? pct(v.complete, v.total) : 0;
      var barColor = p >= 100 ? 'var(--ok)' : p >= 50 ? 'var(--accent)' : 'var(--warn)';
      return '<tr>' +
        '<td>' + (v.active ? '<span class="pill ok">Active</span>' : '<span class="pill">Off</span>') + '</td>' +
        '<td>' + esc(v.name) + '</td>' +
        '<td class="num">' + v.total + '</td>' +
        '<td class="num">' + v.waiting + '</td>' +
        '<td class="num">' + v.onstage + '</td>' +
        '<td class="num">' + v.complete + '</td>' +
        '<td class="num">' + v.skipped + '</td>' +
        '<td style="width:150px">' +
          '<div class="bar"><div class="bar-fill" style="width:' + p + '%;background:' + barColor + '"></div></div>' +
          '<div class="muted xs" style="margin-top:.2rem">' + p + '%</div>' +
        '</td>' +
      '</tr>';
    }).join('');
    document.getElementById('venue-panel').innerHTML =
      '<h2>Venue Progress</h2>' +
      '<div style="overflow-x:auto"><table>' +
        '<thead><tr><th>Status</th><th>Venue</th><th class="num">Total</th><th class="num">Waiting</th><th class="num">On stage</th><th class="num">Done</th><th class="num">Skipped</th><th>Progress</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="8" class="muted">No venues configured.</td></tr>') + '</tbody>' +
      '</table></div>';
  }

  function renderLeaderboard(d){
    var rows = d.top_schools.map(function(s, i){
      return '<tr>' +
        '<td class="num">' + (i + 1) + '</td>' +
        '<td>' + esc(s.school) + '</td>' +
        '<td class="num">' + s.first + '</td>' +
        '<td class="num">' + s.second + '</td>' +
        '<td class="num">' + s.third + '</td>' +
        '<td class="num"><strong>' + s.total + '</strong></td>' +
      '</tr>';
    }).join('');
    document.getElementById('leaderboard-panel').innerHTML =
      '<h2>Top Schools</h2>' +
      '<div style="overflow-x:auto"><table>' +
        '<thead><tr><th>#</th><th>School</th><th class="num">1st</th><th class="num">2nd</th><th class="num">3rd</th><th class="num">Total</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="6" class="muted">No scored events yet.</td></tr>') + '</tbody>' +
      '</table></div>';
  }

  function renderHealth(d){
    var h = d.health;
    document.getElementById('health-panel').innerHTML =
      '<h2>System Health</h2>' +
      '<div class="kv">' +
        '<span>DB size</span><b>' + esc(fmtBytes(h.db_bytes)) + '</b>' +
        '<span>Disk free</span><b>' + esc(fmtBytes(h.disk_free_bytes)) + '</b>' +
        '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
        '<span>Auth failures (24h)</span><b>' + h.auth_failures_24h + '</b>' +
        '<span>Last updated</span><b>' + esc(fmtTime(d.updated_at)) + '</b>' +
      '</div>';
  }

  function renderRecentScores(d){
    var rows = d.recent_scores.map(function(s){
      return '<tr>' +
        '<td class="small">' + esc(fmtTime(s.entered_at)) + '</td>' +
        '<td class="mono small">' + esc(s.event_code) + '</td>' +
        '<td class="small">' + esc(s.school || '—') + '</td>' +
        '<td class="num small">J' + s.judge_no + ' · ' + Number(s.value).toFixed(2) + '</td>' +
      '</tr>';
    }).join('');
    document.getElementById('recent-scores-panel').innerHTML =
      '<h2>Recent Score Entries</h2>' +
      '<table><thead><tr><th>Time</th><th>Event</th><th>School</th><th class="num">Score</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="4" class="muted">No entries yet.</td></tr>') + '</tbody>' +
      '</table>';
  }

  function renderRecentCompleted(d){
    var rows = d.recent_completed.map(function(c){
      return '<tr>' +
        '<td class="small">' + esc(fmtTime(c.completed_at)) + '</td>' +
        '<td class="mono small">' + esc(c.event_code) + '</td>' +
        '<td class="small">' + esc(c.school || '—') + '</td>' +
      '</tr>';
    }).join('');
    document.getElementById('recent-completed-panel').innerHTML =
      '<h2>Recently Completed</h2>' +
      '<table><thead><tr><th>Time</th><th>Event</th><th>School</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="3" class="muted">No completions yet.</td></tr>') + '</tbody>' +
      '</table>';
  }

  async function load(){
    if (loading) return;
    loading = true;
    try {
      var r = await A.api('/api/v1/admin/dashboard');
      if (!r.ok){
        if (r.status === 401 || r.status === 403) return;
        document.getElementById('kpi-grid').innerHTML =
          '<div class="panel"><p class="muted">Failed to load stats (' + r.status + ').</p></div>';
        return;
      }
      renderKPIs(r.data);
      renderVenues(r.data);
      renderLeaderboard(r.data);
      renderHealth(r.data);
      renderRecentScores(r.data);
      renderRecentCompleted(r.data);
    } finally {
      loading = false;
    }
  }

  function startAutoRefresh(){
    if (timer) clearInterval(timer);
    timer = setInterval(load, REFRESH_MS);
  }

  window.onKalLogin = function(info){
    var role = String(info.role || '').toLowerCase();
    if (role !== 'admin'){
      document.getElementById('login-msg').textContent =
        'Dashboard requires an admin account. Sign out and use an admin login.';
      return;
    }
    document.body.classList.remove('login-body');
    var card = document.querySelector('.login-card');
    if (card) card.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent =
      (info.email || info.username || 'admin') + ' · admin';
    load();
    startAutoRefresh();
  };

  document.addEventListener('DOMContentLoaded', function(){
    var refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', load);
    var logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', window.KalAuth.logout);
    window.KalAuth.init();
  });
})();
