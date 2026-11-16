(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var viewEl;
  var cache = { venues: [], events: [], users: [] };
  var partSearchQ = '';

  function adminCall(path, opts){ return A.api('/api/v1/admin' + path, opts); }

  function show(tab){
    document.querySelectorAll('.tab').forEach(function(b){ b.classList.toggle('active', b.dataset.tab === tab); });
    viewEl.innerHTML = '<div class="panel"><p class="muted">Loading…</p></div>';
    return VIEWS[tab]().then(function(html){
      viewEl.innerHTML = html;
      if (typeof MOUNTS[tab] === 'function') MOUNTS[tab]();
    });
  }

  async function fetchVenues(){
    var r = await adminCall('/venues');
    cache.venues = r.ok ? r.data.venues : [];
    return cache.venues;
  }

  var VIEWS = {};
  var MOUNTS = {};

  VIEWS.venues = async function(){
    var vs = await fetchVenues();
    var rows = vs.map(function(v){
      return '<tr><td>' + v.id + '</td><td>' + esc(v.name) + '</td><td>' + esc(v.kind) + '</td>' +
        '<td>' + (v.active ? '✅' : '⛔') + '</td>' +
        '<td><button data-edit-v="' + v.id + '">Edit</button> <button class="danger" data-del-v="' + v.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Venues (' + vs.length + ')</h2>' +
      '<table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Active</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New venue</h3><form id="venue-form" class="row">' +
      '<input id="v-name" placeholder="Name" required maxlength="120" style="flex:1">' +
      '<select id="v-kind"><option>stage</option><option>room</option><option>hall</option><option>ground</option></select>' +
      '<button class="primary" type="submit">Add</button></form></div>';
  };

  MOUNTS.venues = function(){
    document.getElementById('venue-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/venues', { method: 'POST', body: {
        name: document.getElementById('v-name').value.trim(),
        kind: document.getElementById('v-kind').value, active: true
      } });
      if (r.ok){ A.toast('Venue created.'); show('venues'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-edit-v]').forEach(function(b){
      b.addEventListener('click', async function(){
        var id = Number(b.dataset.editV), v = cache.venues.find(function(x){ return x.id === id; });
        if (!v) return;
        var name = prompt('Venue name:', v.name); if (name == null) return;
        var kind = prompt('Kind:', v.kind); if (kind == null) return;
        var active = confirm('Active? (OK = active, Cancel = disabled)');
        var r = await adminCall('/venues/' + id, { method: 'PUT', body: { name: name.trim(), kind: kind.trim(), active: active } });
        if (r.ok){ A.toast('Updated.'); show('venues'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
    viewEl.querySelectorAll('[data-del-v]').forEach(function(b){
      b.addEventListener('click', async function(){
        if (!confirm('Delete this venue?')) return;
        var r = await adminCall('/venues/' + b.dataset.delV, { method: 'DELETE' });
        if (r.ok){ A.toast('Deleted.'); show('venues'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
  };

  VIEWS.events = async function(){
    await Promise.all([
      adminCall('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }),
      fetchVenues()
    ]);
    var rows = cache.events.map(function(e){
      var ven = cache.venues.find(function(v){ return v.id === e.venue_id; });
      return '<tr><td>' + esc(e.code) + '</td><td>' + esc(e.title) + '</td>' +
        '<td>' + esc(e.category || '—') + '</td><td>' + esc(ven ? ven.name : '—') + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td>' +
        '<td><button data-edit-e="' + e.id + '">Edit</button> <button class="danger" data-del-e="' + e.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Events (' + cache.events.length + ')</h2>' +
      '<table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th><th>When</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New event</h3><form id="event-form" class="row">' +
      '<input id="e-code" placeholder="Code" required style="width:7rem">' +
      '<input id="e-title" placeholder="Title" required style="flex:1;min-width:11rem">' +
      '<input id="e-cat" placeholder="Category (e.g. HS General)" maxlength="64" style="width:11rem">' +
      '<select id="e-venue"><option value="">— venue —</option>' +
        cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') + '</select>' +
      '<input id="e-day" placeholder="Day 1" style="width:6rem"><input id="e-time" placeholder="09:00" style="width:6rem">' +
      '<button class="primary" type="submit">Add</button></form></div>';
  };

  MOUNTS.events = function(){
    document.getElementById('event-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/events', { method: 'POST', body: {
        code: document.getElementById('e-code').value.trim(),
        title: document.getElementById('e-title').value.trim(),
        category: document.getElementById('e-cat').value.trim() || null,
        venue_id: Number(document.getElementById('e-venue').value) || null,
        day: document.getElementById('e-day').value.trim() || null,
        scheduled_time: document.getElementById('e-time').value.trim() || null
      } });
      if (r.ok){ A.toast('Event created.'); show('events'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-edit-e]').forEach(function(b){
      b.addEventListener('click', async function(){
        var id = Number(b.dataset.editE), e = cache.events.find(function(x){ return x.id === id; });
        if (!e) return;
        var code = prompt('Code:', e.code); if (code == null) return;
        var title = prompt('Title:', e.title); if (title == null) return;
        var cat = prompt('Category:', e.category || ''); if (cat == null) return;
        var day = prompt('Day (blank = none):', e.day || ''); if (day == null) return;
        var time = prompt('Time (blank = none):', e.scheduled_time || ''); if (time == null) return;
        var r = await adminCall('/events/' + id, { method: 'PUT', body: {
          code: code.trim(), title: title.trim(), category: cat.trim() || null,
          day: day.trim() || null, scheduled_time: time.trim() || null
        } });
        if (r.ok){ A.toast('Updated.'); show('events'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
    viewEl.querySelectorAll('[data-del-e]').forEach(function(b){
      b.addEventListener('click', async function(){
        if (!confirm('Delete this event?')) return;
        var r = await adminCall('/events/' + b.dataset.delE, { method: 'DELETE' });
        if (r.ok){ A.toast('Deleted.'); show('events'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
  };

  VIEWS.participants = async function(){
    await fetchVenues();
    var qs = partSearchQ ? ('?q=' + encodeURIComponent(partSearchQ)) : '';
    var r = await adminCall('/participants' + qs);
    if (!r.ok) return '<div class="panel"><p class="err">Failed to load participants (' + r.status + ').</p></div>';
    var rows = (r.data.participants || []).map(function(p){
      return '<tr><td class="mono">' + esc(p.register_no) + '</td><td>' + esc(p.name) + '</td>' +
        '<td>' + esc(p.school_name) + ' <span class="muted small">(' + esc(p.school_code) + ')</span></td>' +
        '<td>' + p.student_class + '</td><td><span class="pill">' + p.entry_count + ' items</span></td>' +
        '<td><button class="small" data-edit-p="' + p.id + '">Edit</button> ' +
        '<button class="danger small" data-del-p="' + p.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><div class="row" style="margin-bottom:1rem">' +
      '<h2>Participants <span class="badge">' + r.data.total + '</span></h2>' +
      '<input id="p-search" placeholder="Search reg no or name…" value="' + esc(partSearchQ) + '" style="max-width:16rem">' +
      '<span class="spacer" style="flex:1"></span>' +
      '<button id="p-import-btn">Import CSV</button><button id="p-export-btn">Export CSV</button>' +
      '<button id="p-add-btn" class="primary">+ Participant</button>' +
      '<input type="file" id="csv-upload" style="display:none" accept=".csv"></div>' +
      '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Reg No</th><th>Name</th><th>School</th><th>Class</th><th>Entries</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="muted center">No participants found.</td></tr>') + '</tbody></table></div></div>';
  };

  async function openPartEditor(id){
    var dlg = document.getElementById('part-edit-dialog');
    document.getElementById('pe-id').value = id || '';
    ['pe-reg', 'pe-name', 'pe-school', 'pe-scode', 'pe-class'].forEach(function(k){ document.getElementById(k).value = ''; });
    var sec = document.getElementById('pe-entries-section'), list = document.getElementById('pe-entries-list');
    document.getElementById('pe-entry-venue').innerHTML = cache.venues.map(function(v){
      return '<option value="' + v.id + '">' + esc(v.name) + '</option>';
    }).join('');

    if (id){
      var r = await adminCall('/participants/' + id);
      if (!r.ok){ A.toast('Load failed', true); return; }
      var p = r.data.participant;
      document.getElementById('pe-reg').value = p.register_no;
      document.getElementById('pe-name').value = p.name;
      document.getElementById('pe-school').value = p.school_name;
      document.getElementById('pe-scode').value = p.school_code;
      document.getElementById('pe-class').value = p.student_class;
      sec.style.display = 'block';
      var entries = r.data.entries || [];
      list.innerHTML = entries.length ? entries.map(function(e){
        return '<div class="row" style="border-bottom:1px solid var(--border);padding:.4rem 0">' +
          '<span style="flex:1"><b>' + esc(e.item_code) + '</b> · ' + esc(e.venue_name) + ' · ' + esc(e.perf_date) + '</span>' +
          '<button type="button" class="danger small" data-del-entry="' + e.id + '">Remove</button></div>';
      }).join('') : '<p class="muted small">No items added yet.</p>';
    } else {
      sec.style.display = 'none';
      list.innerHTML = '';
    }
    if (!dlg.open) dlg.showModal();
  }

  MOUNTS.participants = function(){
    var sInput = document.getElementById('p-search'), tmr;
    sInput.addEventListener('input', function(){
      clearTimeout(tmr);
      partSearchQ = sInput.value.trim();
      tmr = setTimeout(function(){ show('participants'); }, 280);
    });
    document.getElementById('p-add-btn').addEventListener('click', function(){ openPartEditor(null); });
    document.getElementById('p-export-btn').addEventListener('click', function(){
      A.downloadBlob('/api/v1/admin/participants/export.csv', 'participants.csv');
    });
    var up = document.getElementById('csv-upload');
    document.getElementById('p-import-btn').addEventListener('click', function(){ up.click(); });
    up.addEventListener('change', async function(){
      var file = up.files[0]; if (!file) return;
      var fd = new FormData(); fd.append('file', file);
      var r = await adminCall('/participants/import', { method: 'POST', body: fd });
      up.value = '';
      if (r.ok){
        var d = r.data;
        A.toast('Imported: +' + d.participants_created + ' participants, +' + d.entries_created + ' entries (' + d.errors.length + ' errors)');
        if (d.errors.length) alert(d.errors.slice(0, 15).join('\n'));
        show('participants');
      } else A.toast('Import failed: ' + (r.detail || r.status), true);
    });
    viewEl.querySelectorAll('[data-edit-p]').forEach(function(b){
      b.addEventListener('click', function(){ openPartEditor(Number(b.dataset.editP)); });
    });
    viewEl.querySelectorAll('[data-del-p]').forEach(function(b){
      b.addEventListener('click', async function(){
        if (!confirm('Delete this participant?')) return;
        var r = await adminCall('/participants/' + b.dataset.delP, { method: 'DELETE' });
        if (r.ok){ A.toast('Deleted.'); show('participants'); } else A.toast('Delete failed', true);
      });
    });
  };

  VIEWS.users = async function(){
    await fetchVenues();
    var r = await adminCall('/users');
    if (!r.ok) return '<div class="panel">Failed to load users.</div>';
    cache.users = r.data.users;
    var rows = cache.users.map(function(u){
      var stages = [];
      try {
        stages = JSON.parse(u.stages || '[]').map(function(id){
          var v = cache.venues.find(function(x){ return x.id === id; });
          return v ? v.name : ('#' + id);
        });
      } catch(e){}
      return '<tr><td>' + esc(u.email) + '</td><td>' + esc((u.roles || []).join(', ') || '—') + '</td>' +
        '<td>' + esc(stages.join(', ') || '—') + '</td><td>' + (u.disabled ? '⛔ Disabled' : '✅ Active') + '</td>' +
        '<td><button data-edit-u="' + esc(u.id) + '">Edit</button> ' +
        (u.disabled ? '<button data-enable-u="' + esc(u.id) + '">Enable</button>' : '<button class="danger" data-dis="' + esc(u.id) + '">Disable</button>') + '</td></tr>';
    }).join('');
    var stageOpts = cache.venues.map(function(v){
      return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem 0 0">' +
        '<input type="checkbox" class="u-stage" value="' + v.id + '" style="width:auto;margin:0"> ' + esc(v.name) + '</label>';
    }).join('');
    return '<div class="panel"><h2>Staff accounts (' + cache.users.length + ')</h2>' +
      '<table><thead><tr><th>Email</th><th>Role</th><th>Stages</th><th>Status</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New account</h3><form id="user-form" class="row">' +
      '<input id="u-email" type="email" placeholder="email@example.com" required style="flex:1">' +
      '<input id="u-pass" type="password" placeholder="password (12+)" required minlength="12" style="flex:1">' +
      '<select id="u-role"><option value="stagemaster">stagemaster</option><option value="dataworker">dataworker</option><option value="admin">admin</option></select>' +
      '<button class="primary" type="submit">Create</button></form>' +
      '<p class="small muted" style="margin-top:.8rem">Assign stages (for stagemasters):</p><div class="row">' + stageOpts + '</div></div>';
  };

  MOUNTS.users = function(){
    document.getElementById('user-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var stages = Array.from(viewEl.querySelectorAll('.u-stage:checked')).map(function(x){ return Number(x.value); });
      var r = await adminCall('/users', { method: 'POST', body: {
        email: document.getElementById('u-email').value.trim().toLowerCase(),
        role: document.getElementById('u-role').value, stages: stages, password: document.getElementById('u-pass').value
      } });
      if (r.ok){ A.toast('Created.'); show('users'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-dis]').forEach(function(b){
      b.addEventListener('click', async function(){
        if (!confirm('Disable this account?')) return;
        var r = await adminCall('/users/' + b.dataset.dis + '/disable', { method: 'POST' });
        if (r.ok){ A.toast('Disabled.'); show('users'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
    viewEl.querySelectorAll('[data-enable-u]').forEach(function(b){
      b.addEventListener('click', async function(){
        var r = await adminCall('/users/' + b.dataset.enableU + '/enable', { method: 'POST' });
        if (r.ok){ A.toast('Enabled.'); show('users'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
    viewEl.querySelectorAll('[data-edit-u]').forEach(function(b){
      b.addEventListener('click', function(){
        var u = cache.users.find(function(x){ return x.id === b.dataset.editU; });
        if (!u) return;
        document.getElementById('u-edit-id').value = u.id;
        document.getElementById('u-edit-email').value = u.email;
        document.getElementById('u-edit-role').value = (u.roles && u.roles[0]) || 'stagemaster';
        document.getElementById('u-edit-active').value = u.disabled ? '0' : '1';
        var assigned = [];
        try { assigned = JSON.parse(u.stages || '[]'); } catch(e){}
        document.getElementById('u-edit-stages').innerHTML = cache.venues.map(function(v){
          return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem .3rem 0">' +
            '<input type="checkbox" class="u-edit-stage" value="' + v.id + '"' + (assigned.indexOf(v.id) >= 0 ? ' checked' : '') + ' style="width:auto;margin:0"> ' + esc(v.name) + '</label>';
        }).join('');
        document.getElementById('u-pass-id').value = u.id;
        document.getElementById('user-dialog').showModal();
      });
    });
  };

  VIEWS.audit = async function(){
    var r = await adminCall('/audit?limit=200');
    if (!r.ok) return '<div class="panel">Failed to load audit log.</div>';
    var rows = r.data.items.map(function(a){
      return '<tr><td class="small mono">' + esc(new Date((a.ts || 0) * 1000).toLocaleString()) + '</td>' +
        '<td>' + esc(a.username || '—') + '</td><td class="small mono">' + esc((a.ip_hash || '').slice(0, 10)) + '…</td>' +
        '<td>' + esc(a.event) + '</td><td class="small">' + esc(a.detail || '') + '</td></tr>';
    }).join('');
    return '<div class="panel"><h2>Audit log (latest 200)</h2>' +
      '<table><thead><tr><th>Time</th><th>User</th><th>IP hash</th><th>Event</th><th>Detail</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>';
  };

  VIEWS.ops = async function(){
    var res = await Promise.all([adminCall('/health'), adminCall('/stats')]);
    if (!res[0].ok) return '<div class="panel">Health check failed.</div>';
    var h = res[0].data, st = res[1].ok ? res[1].data : {};
    var labels = { venues: 'Venues', active_venues: 'Active venues', events: 'Events', participants: 'Participants', entries: 'Item entries', photos_published: 'Published photos' };
    var kv = Object.keys(labels).map(function(k){ return '<span>' + labels[k] + '</span><b>' + (st[k] != null ? st[k] : '—') + '</b>'; }).join('');
    return '<div class="panel"><h2>Data</h2><div class="kv">' + kv + '</div></div>' +
      '<div class="panel"><h2>System</h2><div class="kv">' +
        '<span>DB size</span><b>' + (h.db_bytes / 1024).toFixed(1) + ' KB</b>' +
        '<span>Disk free</span><b>' + (h.disk_free_bytes / 1e9).toFixed(2) + ' GB</b>' +
        '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
        '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b>' +
      '</div></div>' +
      '<div class="panel"><h2>Operations</h2><div class="row">' +
        '<button id="op-backup" class="primary">💾 Backup database</button>' +
        '<a class="btn" href="' + esc(A.url('/api/v1/admin/participants/export.csv')) + '" download>⬇ Registry CSV</a>' +
      '</div></div>';
  };

  MOUNTS.ops = function(){
    document.getElementById('op-backup').addEventListener('click', async function(){
      this.disabled = true;
      try {
        var r = await adminCall('/backup', { method: 'POST' });
        A.toast(r.ok ? 'Backup saved.' : 'Backup failed', !r.ok);
      } finally { this.disabled = false; }
    });
  };

  function wireDialogs(){
    document.getElementById('user-edit-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var id = document.getElementById('u-edit-id').value;
      var stages = Array.from(document.querySelectorAll('.u-edit-stage:checked')).map(function(x){ return Number(x.value); });
      var r = await adminCall('/users/' + id, { method: 'PUT', body: {
        email: document.getElementById('u-edit-email').value.trim().toLowerCase(),
        role: document.getElementById('u-edit-role').value,
        is_active: document.getElementById('u-edit-active').value === '1',
        stages: stages
      } });
      if (r.ok){ A.toast('Saved.'); document.getElementById('user-dialog').close(); show('users'); }
      else A.toast('Failed: ' + (r.detail || ''), true);
    });
    document.getElementById('user-password-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/users/' + document.getElementById('u-pass-id').value + '/reset-password', {
        method: 'POST', body: { password: document.getElementById('u-pass-new').value }
      });
      if (r.ok){ A.toast('Password reset.'); document.getElementById('u-pass-new').value = ''; document.getElementById('user-dialog').close(); }
      else A.toast('Failed: ' + (r.detail || ''), true);
    });
    document.querySelectorAll('[data-cancel-user]').forEach(function(b){
      b.addEventListener('click', function(){ document.getElementById('user-dialog').close(); });
    });

    var pDlg = document.getElementById('part-edit-dialog');
    pDlg.addEventListener('click', async function(ev){
      if (ev.target.hasAttribute('data-cancel-part')) pDlg.close();
      var del = ev.target.closest('[data-del-entry]');
      if (del && confirm('Remove this item?')){
        var pid = Number(document.getElementById('pe-id').value);
        var r = await adminCall('/participants/' + pid + '/entries/' + del.dataset.delEntry, { method: 'DELETE' });
        if (r.ok){ A.toast('Item removed.'); openPartEditor(pid); show('participants'); }
      }
    });
    document.getElementById('part-edit-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var id = document.getElementById('pe-id').value;
      var payload = {
        register_no: document.getElementById('pe-reg').value.trim(),
        name: document.getElementById('pe-name').value.trim(),
        school_name: document.getElementById('pe-school').value.trim(),
        school_code: document.getElementById('pe-scode').value.trim(),
        class: Number(document.getElementById('pe-class').value)
      };
      var r = await adminCall(id ? '/participants/' + id : '/participants', { method: id ? 'PUT' : 'POST', body: payload });
      if (r.ok){
        A.toast('Participant saved.');
        if (!id && r.data && r.data.id) openPartEditor(r.data.id);
        show('participants');
      } else A.toast('Save failed: ' + (r.detail || r.status), true);
    });
    document.getElementById('pe-entry-add-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var pid = Number(document.getElementById('pe-id').value);
      var vid = Number(document.getElementById('pe-entry-venue').value);
      var vObj = cache.venues.find(function(x){ return x.id === vid; });
      var r = await adminCall('/participants/' + pid + '/entries', { method: 'POST', body: {
        item_code: document.getElementById('pe-item-code').value.trim(),
        venue_id: vid, venue_name: vObj ? vObj.name : 'Stage',
        perf_date: document.getElementById('pe-entry-date').value
      } });
      if (r.ok){ document.getElementById('pe-item-code').value = ''; A.toast('Entry added.'); openPartEditor(pid); show('participants'); }
      else A.toast('Failed: ' + (r.detail || r.status), true);
    });
  }

  window.onKalLogin = function(info){
    if (String(info.role || '').toLowerCase() !== 'admin'){
      document.getElementById('login-msg').textContent = 'Admin console only.';
      return;
    }
    document.body.classList.remove('login-body');
    var lc = document.querySelector('.login-card'); if (lc) lc.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent = (info.email || 'admin') + ' · admin';
    show('venues');
  };

  document.addEventListener('DOMContentLoaded', function(){
    viewEl = document.getElementById('view');
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('tabs').addEventListener('click', function(ev){
      var t = ev.target.closest('.tab');
      if (t) show(t.dataset.tab);
    });
    wireDialogs();
    window.KalAuth.init();
  });
})();
