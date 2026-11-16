(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var viewEl;
  var cache = { venues: [], categories: [], events: [], users: [], queueItems: [] };
  var partSearchQ = '';

  function adminCall(path, opts){ return A.api('/api/v1/admin' + path, opts); }

  function show(tab){
    document.querySelectorAll('.tab').forEach(function(b){
      b.classList.toggle('active', b.dataset.tab === tab);
    });
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

  // ── Venues ────────────────────────────────────────────────────────────────
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
    var form = document.getElementById('venue-form');
    if (form) form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/venues', { method: 'POST', body: {
        name: document.getElementById('v-name').value.trim(),
        kind: document.getElementById('v-kind').value, active: true
      } });
      if (r.ok){ A.toast('Venue created.'); show('venues'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-edit-v]').forEach(function(b){
      b.addEventListener('click', async function(){
        var id = Number(b.dataset.editV);
        var v = cache.venues.find(function(x){ return x.id === id; });
        if (!v) return;
        var name = prompt('Venue name:', v.name); if (name == null) return;
        var kind = prompt('Kind (stage/room/hall/ground):', v.kind); if (kind == null) return;
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

  // ── Categories ────────────────────────────────────────────────────────────
  VIEWS.categories = async function(){
    var r = await adminCall('/categories');
    cache.categories = r.ok ? r.data.categories : [];
    var rows = cache.categories.map(function(c){
      return '<tr><td>' + c.id + '</td><td>' + esc(c.name) + '</td><td>' + esc(c.grp) + '</td>' +
        '<td><button data-edit-c="' + c.id + '">Edit</button> <button class="danger" data-del-c="' + c.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Categories (' + cache.categories.length + ')</h2>' +
      '<table><thead><tr><th>ID</th><th>Name</th><th>Group</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="4" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New category</h3><form id="cat-form" class="row">' +
      '<input id="c-name" placeholder="Name" required maxlength="120" style="flex:1">' +
      '<input id="c-group" placeholder="Group" maxlength="64" style="flex:1" value="HSS GENERAL">' +
      '<button class="primary" type="submit">Add</button></form></div>';
  };

  MOUNTS.categories = function(){
    var form = document.getElementById('cat-form');
    if (form) form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/categories', { method: 'POST', body: {
        name: document.getElementById('c-name').value.trim(),
        group: document.getElementById('c-group').value.trim() || 'HSS GENERAL'
      } });
      if (r.ok){ A.toast('Category created.'); show('categories'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-edit-c]').forEach(function(b){
      b.addEventListener('click', async function(){
        var id = Number(b.dataset.editC);
        var c = cache.categories.find(function(x){ return x.id === id; });
        if (!c) return;
        var name = prompt('Category name:', c.name); if (name == null) return;
        var group = prompt('Group:', c.grp); if (group == null) return;
        var r = await adminCall('/categories/' + id, { method: 'PUT', body: { name: name.trim(), group: group.trim() } });
        if (r.ok){ A.toast('Updated.'); show('categories'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
    viewEl.querySelectorAll('[data-del-c]').forEach(function(b){
      b.addEventListener('click', async function(){
        if (!confirm('Delete this category?')) return;
        var r = await adminCall('/categories/' + b.dataset.delC, { method: 'DELETE' });
        if (r.ok){ A.toast('Deleted.'); show('categories'); } else A.toast('Failed: ' + (r.detail || ''), true);
      });
    });
  };

  // ── Events ────────────────────────────────────────────────────────────────
  VIEWS.events = async function(){
    await Promise.all([
      adminCall('/categories').then(function(r){ if (r.ok) cache.categories = r.data.categories; }),
      adminCall('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }),
      fetchVenues()
    ]);
    var rows = cache.events.map(function(e){
      var cat = cache.categories.find(function(c){ return c.id === e.category_id; });
      var ven = cache.venues.find(function(v){ return v.id === e.venue_id; });
      return '<tr><td>' + esc(e.code) + '</td><td>' + esc(e.title) + '</td>' +
        '<td>' + esc(cat ? cat.name : '—') + '</td><td>' + esc(ven ? ven.name : '—') + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td>' +
        '<td><button data-edit-e="' + e.id + '">Edit</button> <button class="danger" data-del-e="' + e.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel"><h2>Events (' + cache.events.length + ')</h2>' +
      '<table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th><th>When</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="6" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New event</h3><form id="event-form" class="row">' +
      '<input id="e-code" placeholder="Code" required style="width:8rem">' +
      '<input id="e-title" placeholder="Title" required style="flex:1;min-width:12rem">' +
      '<select id="e-cat"><option value="">— category —</option>' +
        cache.categories.map(function(c){ return '<option value="' + c.id + '">' + esc(c.name) + '</option>'; }).join('') + '</select>' +
      '<select id="e-venue"><option value="">— venue —</option>' +
        cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') + '</select>' +
      '<input id="e-day" placeholder="Day 1" style="width:6rem"><input id="e-time" placeholder="09:00" style="width:6rem">' +
      '<button class="primary" type="submit">Add</button></form></div>';
  };

  MOUNTS.events = function(){
    var form = document.getElementById('event-form');
    if (form) form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var r = await adminCall('/events', { method: 'POST', body: {
        code: document.getElementById('e-code').value.trim(),
        title: document.getElementById('e-title').value.trim(),
        category_id: Number(document.getElementById('e-cat').value) || null,
        venue_id: Number(document.getElementById('e-venue').value) || null,
        day: document.getElementById('e-day').value.trim() || null,
        scheduled_time: document.getElementById('e-time').value.trim() || null
      } });
      if (r.ok){ A.toast('Event created.'); show('events'); } else A.toast('Failed: ' + (r.detail || ''), true);
    });
    viewEl.querySelectorAll('[data-edit-e]').forEach(function(b){
      b.addEventListener('click', async function(){
        var id = Number(b.dataset.editE);
        var e = cache.events.find(function(x){ return x.id === id; });
        if (!e) return;
        var code = prompt('Code:', e.code); if (code == null) return;
        var title = prompt('Title:', e.title); if (title == null) return;
        var day = prompt('Day (blank = none):', e.day || ''); if (day == null) return;
        var time = prompt('Time (blank = none):', e.scheduled_time || ''); if (time == null) return;
        var r = await adminCall('/events/' + id, { method: 'PUT', body: {
          code: code.trim(), title: title.trim(), day: day.trim() || null, scheduled_time: time.trim() || null
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

  // ── Participants Registry ─────────────────────────────────────────────────
  VIEWS.participants = async function(){
    await fetchVenues();
    var qs = partSearchQ ? ('?q=' + encodeURIComponent(partSearchQ)) : '';
    var r = await adminCall('/participants' + qs);
    if (!r.ok) return '<div class="panel"><p class="err">Failed to load participants (' + r.status + ').</p></div>';
    var data = r.data.participants || [];
    var rows = data.map(function(p){
      return '<tr><td class="mono">' + esc(p.register_no) + '</td><td>' + esc(p.name) + '</td>' +
        '<td>' + esc(p.school_name) + ' <span class="muted small">(' + esc(p.school_code) + ')</span></td>' +
        '<td>' + p.student_class + '</td><td><span class="pill">' + p.entry_count + ' items</span></td>' +
        '<td><button class="small" data-edit-p="' + p.id + '">Edit</button> ' +
        '<button class="danger small" data-del-p="' + p.id + '">Delete</button></td></tr>';
    }).join('');
    return '<div class="panel">' +
      '<div class="row" style="margin-bottom:1rem">' +
        '<h2>Participants <span class="badge">' + r.data.total + '</span></h2>' +
        '<input id="p-search" placeholder="Search reg no or name…" value="' + esc(partSearchQ) + '" style="max-width:16rem">' +
        '<span class="spacer" style="flex:1"></span>' +
        '<button id="p-import-btn">Import CSV</button>' +
        '<button id="p-export-btn">Export CSV</button>' +
        '<button id="p-add-btn" class="primary">+ Participant</button>' +
        '<input type="file" id="csv-upload" style="display:none" accept=".csv">' +
      '</div>' +
      '<div style="overflow-x:auto"><table class="tbl">' +
        '<thead><tr><th>Reg No</th><th>Name</th><th>School</th><th>Class</th><th>Entries</th><th></th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="6" class="muted center">No participants found.</td></tr>') + '</tbody>' +
      '</table></div></div>';
  };

  async function openPartEditor(id){
    var dlg = document.getElementById('part-edit-dialog');
    if (!dlg) return;
    document.getElementById('pe-id').value = id || '';
    document.getElementById('pe-reg').value = '';
    document.getElementById('pe-name').value = '';
    document.getElementById('pe-school').value = '';
    document.getElementById('pe-scode').value = '';
    document.getElementById('pe-class').value = '';
    var sec = document.getElementById('pe-entries-section');
    var list = document.getElementById('pe-entries-list');
    var vSel = document.getElementById('pe-entry-venue');
    vSel.innerHTML = cache.venues.map(function(v){
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
    var sInput = document.getElementById('p-search');
    var tmr;
    if (sInput) sInput.addEventListener('input', function(){
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
        if (!confirm('Delete this participant and their item entries?')) return;
        var r = await adminCall('/participants/' + b.dataset.delP, { method: 'DELETE' });
        if (r.ok){ A.toast('Deleted.'); show('participants'); } else A.toast('Delete failed', true);
      });
    });
  };

  // ── Queue (Registry-backed) ───────────────────────────────────────────────
  VIEWS.queue = async function(){
    await fetchVenues();
    var vOpts = '<option value="">All venues</option>' + cache.venues.map(function(v){
      return '<option value="' + v.id + '">' + esc(v.name) + '</option>';
    }).join('');
    return '<div class="panel"><div class="row" style="margin-bottom:.8rem">' +
      '<h2 style="margin:0">Stage Queue</h2><span class="spacer" style="flex:1"></span>' +
      '<select id="q-filter" style="width:auto">' + vOpts + '</select>' +
      '<button id="q-refresh">Refresh</button>' +
      '<button id="q-open-add" class="primary">+ Add to Queue</button>' +
      '</div><div id="queue-list"><p class="muted">Loading…</p></div></div>';
  };

  MOUNTS.queue = function(){
    var filterEl = document.getElementById('q-filter');
    async function loadList(venueId){
      var q = venueId ? ('?venue_id=' + venueId) : '';
      var r = await adminCall('/queue' + q);
      var listEl = document.getElementById('queue-list');
      if (!listEl) return;
      if (!r.ok){ listEl.innerHTML = '<p class="muted">Failed to load queue.</p>'; return; }
      cache.queueItems = r.data.items || [];
      if (!cache.queueItems.length){ listEl.innerHTML = '<p class="muted">Queue is empty.</p>'; return; }
      var showMoves = !!venueId;
      var rows = cache.queueItems.map(function(i){
        var v = cache.venues.find(function(x){ return x.id === i.venue_id; });
        return '<tr><td>' + (i.position + 1) + '</td>' +
          '<td>' + esc(v ? v.name : ('#' + i.venue_id)) + '</td>' +
          '<td class="mono">' + (i.chest_no ? '<strong>' + esc(i.chest_no) + '</strong>' : '—') + '</td>' +
          '<td>' + esc(i.event_code) + ' · ' + esc(i.event_title) + '</td>' +
          '<td>' + esc(i.student_name || '—') + ' <span class="muted small">' + (i.roll ? '(' + esc(i.roll) + ')' : '') + '</span>' +
            '<br><span class="muted small">' + esc(i.school || '') + '</span></td>' +
          '<td><span class="status ' + esc(i.status) + '">' + esc(i.status) + '</span></td>' +
          '<td>' +
            '<button class="small" data-edit-q="' + i.id + '">Chest</button> ' +
            (i.status === 'WAITING' ? '<button class="danger small" data-del-q="' + i.id + '">Delete</button>' : '') +
            (showMoves && i.status === 'WAITING'
              ? ' <button class="small" data-move="up" data-id="' + i.id + '">↑</button>' +
                ' <button class="small" data-move="down" data-id="' + i.id + '">↓</button>' : '') +
          '</td></tr>';
      }).join('');
      listEl.innerHTML = '<div style="overflow-x:auto"><table><thead><tr><th>#</th><th>Venue</th><th>Chest</th><th>Event</th><th>Participant</th><th>Status</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';

      listEl.querySelectorAll('[data-edit-q]').forEach(function(b){
        b.addEventListener('click', async function(){
          var id = Number(b.dataset.editQ);
          var it = cache.queueItems.find(function(x){ return x.id === id; });
          var chest = prompt('Chest number (blank to clear):', (it && it.chest_no) || '');
          if (chest == null) return;
          var res = await adminCall('/queue/' + id, { method: 'PUT', body: { chest_no: chest.trim() || null } });
          if (res.ok){ A.toast('Chest updated.'); loadList(filterEl.value); } else A.toast('Failed', true);
        });
      });
      listEl.querySelectorAll('[data-del-q]').forEach(function(b){
        b.addEventListener('click', async function(){
          if (!confirm('Remove this waiting item?')) return;
          var res = await adminCall('/queue/' + b.dataset.delQ, { method: 'DELETE' });
          if (res.ok){ A.toast('Removed.'); loadList(filterEl.value); } else A.toast('Failed: ' + (res.detail || ''), true);
        });
      });
      listEl.querySelectorAll('[data-move]').forEach(function(b){
        b.addEventListener('click', async function(){
          var res = await adminCall('/queue/' + b.dataset.id + '/move', { method: 'POST', body: { direction: b.dataset.move } });
          if (res.ok) loadList(filterEl.value); else A.toast('Move failed', true);
        });
      });
    }

    filterEl.addEventListener('change', function(){ loadList(filterEl.value); });
    document.getElementById('q-refresh').addEventListener('click', function(){ loadList(filterEl.value); });
    document.getElementById('q-open-add').addEventListener('click', function(){
      var dlg = document.getElementById('queue-add-dialog');
      var qaV = document.getElementById('qa-venue');
      qaV.innerHTML = cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('');
      if (filterEl.value) qaV.value = filterEl.value;
      document.getElementById('qa-entry-id').value = '';
      document.getElementById('qa-search').value = '';
      document.getElementById('qa-results').innerHTML = '<p class="muted small">Type at least 2 characters to search…</p>';
      document.getElementById('qa-chest').value = '';
      dlg.showModal();
    });
    window._reloadQueue = function(){ loadList(filterEl.value); };
    loadList('');
  };

  // ── Users ─────────────────────────────────────────────────────────────────
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
    var form = document.getElementById('user-form');
    if (form) form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var stages = Array.from(viewEl.querySelectorAll('.u-stage:checked')).map(function(x){ return Number(x.value); });
      var r = await adminCall('/users', { method: 'POST', body: {
        email: document.getElementById('u-email').value.trim().toLowerCase(),
        role: document.getElementById('u-role').value,
        stages: stages,
        password: document.getElementById('u-pass').value
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
      b.addEventListener('click', function(){ openUserDialog(b.dataset.editU); });
    });
  };

  // ── Audit ─────────────────────────────────────────────────────────────────
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

  // ── Ops ───────────────────────────────────────────────────────────────────
  VIEWS.ops = async function(){
    var res = await Promise.all([adminCall('/health'), adminCall('/stats')]);
    if (!res[0].ok) return '<div class="panel">Health check failed.</div>';
    var h = res[0].data;
    var st = res[1].ok ? res[1].data : {};
    var labels = {
      venues: 'Venues', categories: 'Categories', events: 'Events',
      participants: 'Participants', queue_items: 'Queue items',
      queue_waiting: 'Queue · waiting', queue_onstage: 'Queue · on stage',
      queue_complete: 'Queue · complete'
    };
    var kv = Object.keys(labels).map(function(k){
      return '<span>' + labels[k] + '</span><b>' + (st[k] != null ? st[k] : '—') + '</b>';
    }).join('');
    return '<div class="panel"><h2>Data</h2><div class="kv">' + kv + '</div></div>' +
      '<div class="panel"><h2>System</h2><div class="kv">' +
        '<span>DB size</span><b>' + (h.db_bytes / 1024).toFixed(1) + ' KB</b>' +
        '<span>Disk free</span><b>' + (h.disk_free_bytes / 1e9).toFixed(2) + ' GB</b>' +
        '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
        '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b>' +
      '</div></div>' +
      '<div class="panel"><h2>Operations</h2><div class="row" style="flex-wrap:wrap">' +
        '<button id="op-backup" class="primary">💾 Backup database</button>' +
        '<a class="btn" href="' + esc(A.url('/api/v1/admin/export/participants.csv')) + '" download>⬇ Queue CSV</a>' +
        '<a class="btn" href="' + esc(A.url('/api/v1/admin/participants/export.csv')) + '" download>⬇ Registry CSV</a>' +
      '</div></div>';
  };

  MOUNTS.ops = function(){
    var btn = document.getElementById('op-backup');
    if (btn) btn.addEventListener('click', async function(){
      btn.disabled = true;
      try {
        var r = await adminCall('/backup', { method: 'POST' });
        if (r.ok) A.toast('Backup saved.'); else A.toast('Backup failed', true);
      } finally { btn.disabled = false; }
    });
  };

  // ── Dialogs ───────────────────────────────────────────────────────────────
  function openUserDialog(id){
    var u = cache.users.find(function(x){ return x.id === id; });
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
  }

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
      var id = document.getElementById('u-pass-id').value;
      var pw = document.getElementById('u-pass-new').value;
      var r = await adminCall('/users/' + id + '/reset-password', { method: 'POST', body: { password: pw } });
      if (r.ok){
        A.toast('Password reset.');
        document.getElementById('u-pass-new').value = '';
        document.getElementById('user-dialog').close();
      } else A.toast('Failed: ' + (r.detail || ''), true);
    });

    document.querySelectorAll('[data-cancel-user]').forEach(function(b){
      b.addEventListener('click', function(){ document.getElementById('user-dialog').close(); });
    });

    // Participant create/edit + entries
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
      var vSel = document.getElementById('pe-entry-venue');
      var vid = Number(vSel.value);
      var vObj = cache.venues.find(function(x){ return x.id === vid; });
      var r = await adminCall('/participants/' + pid + '/entries', { method: 'POST', body: {
        item_code: document.getElementById('pe-item-code').value.trim(),
        venue_id: vid,
        venue_name: vObj ? vObj.name : 'Stage',
        perf_date: document.getElementById('pe-entry-date').value
      } });
      if (r.ok){
        A.toast('Entry added.');
        document.getElementById('pe-item-code').value = '';
        openPartEditor(pid);
        show('participants');
      } else A.toast('Failed: ' + (r.detail || r.status), true);
    });

    // Queue Add modal
    var qDlg = document.getElementById('queue-add-dialog');
    var qaSearchTmr;
    document.querySelectorAll('[data-cancel-queue]').forEach(function(b){
      b.addEventListener('click', function(){ qDlg.close(); });
    });
    document.getElementById('qa-search').addEventListener('input', function(){
      clearTimeout(qaSearchTmr);
      var q = this.value.trim();
      var box = document.getElementById('qa-results');
      if (q.length < 2){ box.innerHTML = '<p class="muted small">Type at least 2 characters…</p>'; return; }
      qaSearchTmr = setTimeout(async function(){
        var r = await adminCall('/participants?q=' + encodeURIComponent(q) + '&limit=5');
        if (!r.ok || !r.data.participants.length){ box.innerHTML = '<p class="muted small">No matches.</p>'; return; }
        var details = await Promise.all(r.data.participants.map(function(p){ return adminCall('/participants/' + p.id); }));
        var rows = [];
        details.forEach(function(d){
          if (!d.ok) return;
          var p = d.data.participant;
          (d.data.entries || []).forEach(function(e){
            rows.push(
              '<div class="row" style="border-bottom:1px solid var(--border);padding:.35rem 0">' +
              '<span style="flex:1"><b>' + esc(p.name) + '</b> (' + esc(p.register_no) + ') · Item ' + esc(e.item_code) + '</span>' +
              '<button type="button" class="primary small" data-pick-entry="' + e.id + '" data-pick-label="' + esc(p.name + ' (' + p.register_no + ') - Item ' + e.item_code) + '">Select</button></div>'
            );
          });
        });
        box.innerHTML = rows.join('') || '<p class="muted small">Matching participants have no item entries.</p>';
      }, 280);
    });
    document.getElementById('qa-results').addEventListener('click', function(ev){
      var btn = ev.target.closest('[data-pick-entry]');
      if (!btn) return;
      document.getElementById('qa-entry-id').value = btn.dataset.pickEntry;
      document.getElementById('qa-results').innerHTML = '<p class="ok small">Selected: ' + esc(btn.dataset.pickLabel) + '</p>';
    });
    document.getElementById('queue-add-form').addEventListener('submit', async function(ev){
      ev.preventDefault();
      var eid = Number(document.getElementById('qa-entry-id').value);
      if (!eid){ A.toast('Select a participant entry first.', true); return; }
      var r = await adminCall('/queue', { method: 'POST', body: {
        venue_id: Number(document.getElementById('qa-venue').value),
        participant_entry_id: eid,
        chest_no: document.getElementById('qa-chest').value.trim() || null
      } });
      if (r.ok){
        A.toast('Added to queue.');
        qDlg.close();
        if (window._reloadQueue) window._reloadQueue();
      } else A.toast('Add failed: ' + (r.detail || r.status), true);
    });
  }

  // ── Login & Boot ──────────────────────────────────────────────────────────
  window.onKalLogin = function(info){
    var role = String(info.role || '').toLowerCase();
    if (role !== 'admin'){
      document.getElementById('login-msg').textContent = 'Admin console only. Sign out and use an admin account.';
      return;
    }
    document.body.classList.remove('login-body');
    var lc = document.querySelector('.login-card'); if (lc) lc.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent = (info.email || info.username || 'admin') + ' · admin';
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
