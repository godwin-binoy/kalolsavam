(function(){
  'use strict';
  var A = window.KalAPI, esc = A.esc, el = A.el, viewEl;
  var cache = { venues: [], events: [], users: [] }, partSearchQ = '';
  function call(p, o){ return A.api('/api/v1/admin' + p, o); }
  function req(p, o, msg){ return A.req('/api/v1/admin' + p, o, msg); }

  function show(tab){
    document.querySelectorAll('.tab').forEach(function(b){ b.classList.toggle('active', b.dataset.tab === tab); });
    viewEl.innerHTML = '<div class="panel"><p class="muted">Loading…</p></div>';
    return VIEWS[tab]().then(function(html){
      viewEl.innerHTML = html;
      if (MOUNTS[tab]) MOUNTS[tab]();
    });
  }

  async function fetchVenues(){
    var r = await call('/venues');
    return (cache.venues = r.ok ? r.data.venues : []);
  }

  var VIEWS = {}, MOUNTS = {};

  VIEWS.venues = async function(){
    var vs = await fetchVenues();
    var rows = vs.map(function(v){
      return '<tr><td>' + v.id + '</td><td>' + esc(v.name) + '</td><td>' + esc(v.kind) + '</td><td>' + (v.active ? '✅' : '⛔') + '</td>' +
        '<td><button data-edit-v="' + v.id + '">Edit</button> <button class="danger" data-del="/venues/' + v.id + '" data-tab="venues">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Venues (' + vs.length + ')</h2><table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Active</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New venue</h3><form id="venue-form" class="row"><input id="v-name" placeholder="Name" required maxlength="120" style="flex:1">' +
      '<select id="v-kind"><option>stage</option><option>room</option><option>hall</option><option>ground</option></select><button class="primary" type="submit">Add</button></form></div>';
  };
  MOUNTS.venues = function(){
    el('venue-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      if (await req('/venues', { method: 'POST', body: { name: el('v-name').value.trim(), kind: el('v-kind').value, active: true } }, 'Venue created.')) show('venues');
    });
  };

  VIEWS.events = async function(){
    await Promise.all([call('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }), fetchVenues()]);
    var rows = cache.events.map(function(e){
      var ven = cache.venues.find(function(v){ return v.id === e.venue_id; });
      return '<tr><td>' + esc(e.code) + '</td><td>' + esc(e.title) + '</td><td>' + esc(e.category || '—') + '</td><td>' + esc(ven ? ven.name : '—') + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td>' +
        '<td><button data-edit-e="' + e.id + '">Edit</button> <button class="danger" data-del="/events/' + e.id + '" data-tab="events">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Events (' + cache.events.length + ')</h2><table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th><th>When</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New event</h3><form id="event-form" class="row"><input id="e-code" placeholder="Code" required style="width:7rem">' +
      '<input id="e-title" placeholder="Title" required style="flex:1;min-width:11rem"><input id="e-cat" placeholder="Category (e.g. HS General)" maxlength="64" style="width:11rem">' +
      '<select id="e-venue"><option value="">— venue —</option>' + cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') + '</select>' +
      '<input id="e-day" placeholder="Day 1" style="width:6rem"><input id="e-time" placeholder="09:00" style="width:6rem"><button class="primary" type="submit">Add</button></form></div>';
  };
  MOUNTS.events = function(){
    el('event-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      if (await req('/events', { method: 'POST', body: {
        code: el('e-code').value.trim(), title: el('e-title').value.trim(), category: el('e-cat').value.trim() || null,
        venue_id: Number(el('e-venue').value) || null, day: el('e-day').value.trim() || null, scheduled_time: el('e-time').value.trim() || null
      } }, 'Event created.')) show('events');
    });
  };

  VIEWS.participants = async function(){
    await fetchVenues();
    var r = await call('/participants' + (partSearchQ ? '?q=' + encodeURIComponent(partSearchQ) : ''));
    if (!r.ok) return '<div class="panel"><p class="err">Failed to load participants.</p></div>';
    var rows = (r.data.participants || []).map(function(p){
      return '<tr><td class="mono">' + esc(p.register_no) + '</td><td>' + esc(p.name) + '</td>' +
        '<td>' + esc(p.school_name) + ' <span class="muted small">(' + esc(p.school_code) + ')</span></td><td>' + p.student_class + '</td>' +
        '<td><span class="pill">' + p.entry_count + ' items</span></td>' +
        '<td><button class="small" data-edit-p="' + p.id + '">Edit</button> <button class="danger small" data-del="/participants/' + p.id + '" data-tab="participants">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><div class="row" style="margin-bottom:1rem"><h2>Participants <span class="badge">' + r.data.total + '</span></h2>' +
      '<input id="p-search" placeholder="Search reg no or name…" value="' + esc(partSearchQ) + '" style="max-width:16rem"><span class="spacer" style="flex:1"></span>' +
      '<button id="p-import-btn">Import CSV</button><button id="p-export-btn">Export CSV</button><button id="p-add-btn" class="primary">+ Participant</button>' +
      '<input type="file" id="csv-upload" style="display:none" accept=".csv"></div>' +
      '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Reg No</th><th>Name</th><th>School</th><th>Class</th><th>Entries</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="muted center">No participants found.</td></tr>') + '</tbody></table></div></div>';
  };

  async function openPartEditor(id){
    var dlg = el('part-edit-dialog');
    el('pe-id').value = id || '';
    ['pe-reg', 'pe-name', 'pe-school', 'pe-scode', 'pe-class'].forEach(function(k){ el(k).value = ''; });
    el('pe-entry-venue').innerHTML = cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('');
    var sec = el('pe-entries-section'), list = el('pe-entries-list');
    if (id){
      var d = await req('/participants/' + id);
      if (!d) return;
      var p = d.participant;
      el('pe-reg').value = p.register_no; el('pe-name').value = p.name; el('pe-school').value = p.school_name;
      el('pe-scode').value = p.school_code; el('pe-class').value = p.student_class;
      sec.style.display = 'block';
      list.innerHTML = (d.entries || []).length ? d.entries.map(function(e){
        return '<div class="row" style="border-bottom:1px solid var(--border);padding:.4rem 0">' +
          '<span style="flex:1"><b>' + esc(e.item_code) + '</b> · ' + esc(e.venue_name) + ' · ' + esc(e.perf_date) + '</span>' +
          '<button type="button" class="danger small" data-del-entry="' + e.id + '">Remove</button></div>';
      }).join('') : '<p class="muted small">No items added yet.</p>';
    } else { sec.style.display = 'none'; list.innerHTML = ''; }
    if (!dlg.open) dlg.showModal();
  }

  MOUNTS.participants = function(){
    el('p-search').addEventListener('input', A.debounce(function(){ partSearchQ = this.value.trim(); show('participants'); }, 280));
    el('p-add-btn').addEventListener('click', function(){ openPartEditor(null); });
    el('p-export-btn').addEventListener('click', function(){ A.downloadBlob('/api/v1/admin/participants/export.csv', 'participants.csv'); });
    var up = el('csv-upload');
    el('p-import-btn').addEventListener('click', function(){ up.click(); });
    up.addEventListener('change', async function(){
      var f = up.files[0]; up.value = ''; if (!f) return;
      var fd = new FormData(); fd.append('file', f);
      var d = await req('/participants/import', { method: 'POST', body: fd });
      if (d){
        A.toast('Imported: +' + d.participants_created + ' participants, +' + d.entries_created + ' entries (' + d.errors.length + ' errors)');
        if (d.errors.length) alert(d.errors.slice(0, 15).join('\n'));
        show('participants');
      }
    });
  };

  VIEWS.users = async function(){
    await fetchVenues();
    var r = await call('/users');
    if (!r.ok) return '<div class="panel">Failed to load users.</div>';
    cache.users = r.data.users;
    var rows = cache.users.map(function(u){
      var stages = [];
      try { stages = JSON.parse(u.stages || '[]').map(function(id){ var v = cache.venues.find(function(x){ return x.id === id; }); return v ? v.name : ('#' + id); }); } catch(e){}
      return '<tr><td>' + esc(u.email) + '</td><td>' + esc((u.roles || []).join(', ') || '—') + '</td><td>' + esc(stages.join(', ') || '—') + '</td>' +
        '<td>' + (u.disabled ? '⛔ Disabled' : '✅ Active') + '</td><td><button data-edit-u="' + esc(u.id) + '">Edit</button> ' +
        '<button class="' + (u.disabled ? '' : 'danger') + '" data-toggle-u="' + esc(u.id) + '" data-act="' + (u.disabled ? 'enable' : 'disable') + '">' + (u.disabled ? 'Enable' : 'Disable') + '</button></td></tr>';
    }).join('');
    var stageOpts = cache.venues.map(function(v){
      return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem 0 0"><input type="checkbox" class="u-stage" value="' + v.id + '" style="width:auto;margin:0"> ' + esc(v.name) + '</label>';
    }).join('');
    return '<div class="panel"><h2>Staff accounts (' + cache.users.length + ')</h2><table><thead><tr><th>Email</th><th>Role</th><th>Stages</th><th>Status</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New account</h3><form id="user-form" class="row"><input id="u-email" type="email" placeholder="email@example.com" required style="flex:1">' +
      '<input id="u-pass" type="password" placeholder="password (12+)" required minlength="12" style="flex:1"><select id="u-role"><option value="stagemaster">stagemaster</option><option value="dataworker">dataworker</option><option value="admin">admin</option></select>' +
      '<button class="primary" type="submit">Create</button></form><p class="small muted" style="margin-top:.8rem">Assign stages (stagemasters):</p><div class="row">' + stageOpts + '</div></div>';
  };
  MOUNTS.users = function(){
    el('user-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var stages = Array.from(viewEl.querySelectorAll('.u-stage:checked')).map(function(x){ return Number(x.value); });
      if (await req('/users', { method: 'POST', body: { email: el('u-email').value.trim().toLowerCase(), role: el('u-role').value, stages: stages, password: el('u-pass').value } }, 'Created.')) show('users');
    });
  };

  VIEWS.audit = async function(){
    var r = await call('/audit?limit=200');
    if (!r.ok) return '<div class="panel">Failed to load audit log.</div>';
    var rows = r.data.items.map(function(a){
      return '<tr><td class="small mono">' + esc(new Date((a.ts || 0) * 1000).toLocaleString()) + '</td><td>' + esc(a.username || '—') + '</td>' +
        '<td class="small mono">' + esc((a.ip_hash || '').slice(0, 10)) + '…</td><td>' + esc(a.event) + '</td><td class="small">' + esc(a.detail || '') + '</td></tr>';
    }).join('');
    return '<div class="panel"><h2>Audit log (latest 200)</h2><table><thead><tr><th>Time</th><th>User</th><th>IP hash</th><th>Event</th><th>Detail</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>';
  };

  VIEWS.ops = async function(){
    var res = await Promise.all([call('/health'), call('/stats')]);
    if (!res[0].ok) return '<div class="panel">Health check failed.</div>';
    var h = res[0].data, st = res[1].ok ? res[1].data : {};
    var labels = { venues: 'Venues', active_venues: 'Active venues', events: 'Events', participants: 'Participants', entries: 'Item entries', photos_published: 'Published photos' };
    var kv = Object.keys(labels).map(function(k){ return '<span>' + labels[k] + '</span><b>' + (st[k] != null ? st[k] : '—') + '</b>'; }).join('');
    return '<div class="panel"><h2>Data</h2><div class="kv">' + kv + '</div></div>' +
      '<div class="panel"><h2>System</h2><div class="kv"><span>DB size</span><b>' + (h.db_bytes / 1024).toFixed(1) + ' KB</b>' +
      '<span>Disk free</span><b>' + (h.disk_free_bytes / 1e9).toFixed(2) + ' GB</b><span>SSE connections</span><b>' + h.sse_connections + '</b>' +
      '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b></div></div>' +
      '<div class="panel"><h2>Operations</h2><div class="row"><button id="op-backup" class="primary">💾 Backup database</button>' +
      '<a class="btn" href="' + esc(A.url('/api/v1/admin/participants/export.csv')) + '" download>⬇ Registry CSV</a>' +
      '<button id="op-wipe" class="danger">🗑️ Hard Wipe Database</button></div></div>';
  };
  MOUNTS.ops = function(){
    el('op-backup').addEventListener('click', async function(){
      this.disabled = true;
      try { await req('/backup', { method: 'POST' }, 'Backup saved.'); } finally { this.disabled = false; }
    });
    el('op-wipe').addEventListener('click', async function(){
      if (prompt('Type WIPE to permanently delete all venues, events, participants, and photos:') !== 'WIPE') return;
      this.disabled = true;
      try {
        if (await req('/wipe', { method: 'POST' }, 'Database wiped.')) show('ops');
      } finally { this.disabled = false; }
    });
  };

  function wireGlobalEvents(){
    A.on(el('tabs'), 'click', '.tab', function(t){ show(t.dataset.tab); });
    A.on(viewEl, 'click', '[data-del]', async function(b){
      if (confirm('Delete this item?') && await req(b.dataset.del, { method: 'DELETE' }, 'Deleted.')) show(b.dataset.tab);
    });
    A.on(viewEl, 'click', '[data-edit-v]', async function(b){
      var id = Number(b.dataset.editV), v = cache.venues.find(function(x){ return x.id === id; });
      if (!v) return;
      var name = prompt('Venue name:', v.name); if (name == null) return;
      var kind = prompt('Kind:', v.kind); if (kind == null) return;
      if (await req('/venues/' + id, { method: 'PUT', body: { name: name.trim(), kind: kind.trim(), active: confirm('Active? (OK=yes)') } }, 'Updated.')) show('venues');
    });
    A.on(viewEl, 'click', '[data-edit-e]', async function(b){
      var id = Number(b.dataset.editE), e = cache.events.find(function(x){ return x.id === id; });
      if (!e) return;
      var code = prompt('Code:', e.code); if (code == null) return;
      var title = prompt('Title:', e.title); if (title == null) return;
      var cat = prompt('Category:', e.category || ''); if (cat == null) return;
      var day = prompt('Day (blank = none):', e.day || ''); if (day == null) return;
      var time = prompt('Time (blank = none):', e.scheduled_time || ''); if (time == null) return;
      if (await req('/events/' + id, { method: 'PUT', body: { code: code.trim(), title: title.trim(), category: cat.trim() || null, day: day.trim() || null, scheduled_time: time.trim() || null } }, 'Updated.')) show('events');
    });
    A.on(viewEl, 'click', '[data-edit-p]', function(b){ openPartEditor(Number(b.dataset.editP)); });
    A.on(viewEl, 'click', '[data-toggle-u]', async function(b){
      if ((b.dataset.act !== 'disable' || confirm('Disable this account?')) && await req('/users/' + b.dataset.toggleU + '/' + b.dataset.act, { method: 'POST' }, 'Updated.')) show('users');
    });
    A.on(viewEl, 'click', '[data-edit-u]', function(b){
      var u = cache.users.find(function(x){ return x.id === b.dataset.editU; });
      if (!u) return;
      el('u-edit-id').value = u.id; el('u-edit-email').value = u.email;
      el('u-edit-role').value = (u.roles && u.roles[0]) || 'stagemaster';
      el('u-edit-active').value = u.disabled ? '0' : '1';
      var assigned = []; try { assigned = JSON.parse(u.stages || '[]'); } catch(e){}
      el('u-edit-stages').innerHTML = cache.venues.map(function(v){
        return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem .3rem 0"><input type="checkbox" class="u-edit-stage" value="' + v.id + '"' + (assigned.indexOf(v.id) >= 0 ? ' checked' : '') + ' style="width:auto;margin:0"> ' + esc(v.name) + '</label>';
      }).join('');
      el('u-pass-id').value = u.id;
      el('user-dialog').showModal();
    });

    el('user-edit-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var stages = Array.from(document.querySelectorAll('.u-edit-stage:checked')).map(function(x){ return Number(x.value); });
      if (await req('/users/' + el('u-edit-id').value, { method: 'PUT', body: {
        email: el('u-edit-email').value.trim().toLowerCase(), role: el('u-edit-role').value,
        is_active: el('u-edit-active').value === '1', stages: stages
      } }, 'Saved.')){ el('user-dialog').close(); show('users'); }
    });
    el('user-password-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      if (await req('/users/' + el('u-pass-id').value + '/reset-password', { method: 'POST', body: { password: el('u-pass-new').value } }, 'Password reset.')){
        el('u-pass-new').value = ''; el('user-dialog').close();
      }
    });
    document.querySelectorAll('[data-cancel-user]').forEach(function(b){ b.addEventListener('click', function(){ el('user-dialog').close(); }); });

    var pDlg = el('part-edit-dialog');
    A.on(pDlg, 'click', '[data-cancel-part]', function(){ pDlg.close(); });
    A.on(pDlg, 'click', '[data-del-entry]', async function(b){
      var pid = Number(el('pe-id').value);
      if (confirm('Remove this item?') && await req('/participants/' + pid + '/entries/' + b.dataset.delEntry, { method: 'DELETE' }, 'Item removed.')){
        openPartEditor(pid); show('participants');
      }
    });
    el('part-edit-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var id = el('pe-id').value;
      var d = await req(id ? '/participants/' + id : '/participants', { method: id ? 'PUT' : 'POST', body: {
        register_no: el('pe-reg').value.trim(), name: el('pe-name').value.trim(),
        school_name: el('pe-school').value.trim(), school_code: el('pe-scode').value.trim(), class: Number(el('pe-class').value)
      } }, 'Participant saved.');
      if (d){ if (!id && d.id) openPartEditor(d.id); show('participants'); }
    });
    el('pe-entry-add-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var pid = Number(el('pe-id').value), vid = Number(el('pe-entry-venue').value), vObj = cache.venues.find(function(x){ return x.id === vid; });
      if (await req('/participants/' + pid + '/entries', { method: 'POST', body: {
        item_code: el('pe-item-code').value.trim(), venue_id: vid, venue_name: vObj ? vObj.name : 'Stage', perf_date: el('pe-entry-date').value
      } }, 'Entry added.')){ el('pe-item-code').value = ''; openPartEditor(pid); show('participants'); }
    });
  }

  window.onKalLogin = function(info){
    if (String(info.role || '').toLowerCase() !== 'admin'){ el('login-msg').textContent = 'Admin console only.'; return; }
    document.body.classList.remove('login-body');
    var lc = document.querySelector('.login-card'); if (lc) lc.classList.add('hidden');
    el('app').classList.remove('hidden');
    el('who').textContent = (info.email || 'admin') + ' · admin';
    show('venues');
  };

  document.addEventListener('DOMContentLoaded', function(){
    viewEl = el('view');
    el('logout-btn').addEventListener('click', window.KalAuth.logout);
    wireGlobalEvents();
    window.KalAuth.init();
  });
})();
