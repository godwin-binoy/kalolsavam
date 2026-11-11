(function(){
  'use strict';
  var A = window.KalAPI;
  var viewEl;
  var cache = { venues: [], categories: [], events: [], users: [], queueItems: [] };

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  async function adminCall(path, opts){
    return await A.api('/api/v1/admin' + path, opts);
  }

  var VIEWS = {};

  function show(tab){
    document.querySelectorAll('.tab').forEach(function(b){
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    viewEl.innerHTML = '<div class="panel"><p class="muted">Loading…</p></div>';
    VIEWS[tab]().then(function(html){ viewEl.innerHTML = html; });
  }

  async function fetchVenues(){
    var r = await adminCall('/venues');
    cache.venues = r.ok ? r.data.venues : [];
    return cache.venues;
  }

  // ── Venues ─────────────────────────────────────────────────────────────
  VIEWS.venues = async function(){
    var vs = await fetchVenues();
    var rows = vs.map(function(v){
      return '<tr>' +
        '<td>' + v.id + '</td>' +
        '<td>' + esc(v.name) + '</td>' +
        '<td>' + esc(v.kind) + '</td>' +
        '<td>' + (v.active ? '✅' : '⛔') + '</td>' +
        '<td>' +
          '<button data-edit-v="' + v.id + '">Edit</button> ' +
          '<button class="danger" data-del-v="' + v.id + '">Delete</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    var html =
      '<div class="panel"><h2>Venues (' + vs.length + ')</h2>' +
        '<table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Active</th><th></th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table>' +
      '</div>' +
      '<div class="panel"><h3>New venue</h3>' +
        '<form id="venue-form" class="row">' +
          '<input id="v-name" placeholder="Name" required maxlength="120" style="flex:1">' +
          '<select id="v-kind"><option>stage</option><option>room</option><option>hall</option><option>ground</option></select>' +
          '<button class="primary" type="submit">Add</button>' +
        '</form>' +
      '</div>';

    setTimeout(function(){
      var form = document.getElementById('venue-form');
      if (form) form.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r = await adminCall('/venues', { method: 'POST', body: {
          name: document.getElementById('v-name').value.trim(),
          kind: document.getElementById('v-kind').value, active: true,
        } });
        if (r.ok){ A.toast('Venue created.'); show('venues'); }
        else A.toast('Failed: ' + (r.detail || ''), true);
      });

      viewEl.querySelectorAll('[data-edit-v]').forEach(function(b){
        b.addEventListener('click', async function(){
          var id = Number(b.dataset.editV);
          var v = cache.venues.filter(function(x){ return x.id === id; })[0];
          if (!v) return;
          var name = prompt('Venue name:', v.name);
          if (name == null) return;
          var kind = prompt('Kind (stage/room/hall/ground):', v.kind);
          if (kind == null) return;
          var active = confirm('Active? (OK = active, Cancel = disabled)');
          var r = await adminCall('/venues/' + id, {
            method: 'PUT',
            body: { name: name.trim(), kind: kind.trim(), active: active },
          });
          if (r.ok){ A.toast('Updated.'); show('venues'); }
          else A.toast('Failed: ' + (r.detail || ''), true);
        });
      });

      viewEl.querySelectorAll('[data-del-v]').forEach(function(b){
        b.addEventListener('click', async function(){
          if (!confirm('Delete this venue? This cannot be undone.')) return;
          var r = await adminCall('/venues/' + b.dataset.delV, { method: 'DELETE' });
          if (r.ok){ A.toast('Deleted.'); show('venues'); }
          else A.toast('Failed: ' + (r.detail || ''), true);
        });
      });
    }, 0);

    return html;
  };

  // ── Categories ─────────────────────────────────────────────────────────
  VIEWS.categories = async function(){
    var r = await adminCall('/categories');
    cache.categories = r.ok ? r.data.categories : [];
    var rows = cache.categories.map(function(c){
      return '<tr>' +
        '<td>' + c.id + '</td>' +
        '<td>' + esc(c.name) + '</td>' +
        '<td>' + esc(c.grp) + '</td>' +
        '<td>' +
          '<button data-edit-c="' + c.id + '">Edit</button> ' +
          '<button class="danger" data-del-c="' + c.id + '">Delete</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    var html =
      '<div class="panel"><h2>Categories (' + cache.categories.length + ')</h2>' +
        '<table><thead><tr><th>ID</th><th>Name</th><th>Group</th><th></th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="4" class="muted">none</td></tr>') + '</tbody></table>' +
      '</div>' +
      '<div class="panel"><h3>New category</h3>' +
        '<form id="cat-form" class="row">' +
          '<input id="c-name" placeholder="Name" required maxlength="120" style="flex:1">' +
          '<input id="c-group" placeholder="Group (e.g. HS GENERAL)" maxlength="64" style="flex:1" value="HSS GENERAL">' +
          '<button class="primary" type="submit">Add</button>' +
        '</form>' +
      '</div>';

    setTimeout(function(){
      var form = document.getElementById('cat-form');
      if (form) form.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r2 = await adminCall('/categories', { method: 'POST', body: {
          name: document.getElementById('c-name').value.trim(),
          group: document.getElementById('c-group').value.trim() || 'HSS GENERAL',
        } });
        if (r2.ok){ A.toast('Category created.'); show('categories'); }
        else A.toast('Failed: ' + (r2.detail || ''), true);
      });

      viewEl.querySelectorAll('[data-edit-c]').forEach(function(b){
        b.addEventListener('click', async function(){
          var id = Number(b.dataset.editC);
          var c = cache.categories.filter(function(x){ return x.id === id; })[0];
          if (!c) return;
          var name = prompt('Category name:', c.name);
          if (name == null) return;
          var group = prompt('Group:', c.grp);
          if (group == null) return;
          var r2 = await adminCall('/categories/' + id, {
            method: 'PUT',
            body: { name: name.trim(), group: group.trim() },
          });
          if (r2.ok){ A.toast('Updated.'); show('categories'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });

      viewEl.querySelectorAll('[data-del-c]').forEach(function(b){
        b.addEventListener('click', async function(){
          if (!confirm('Delete this category?')) return;
          var r2 = await adminCall('/categories/' + b.dataset.delC, { method: 'DELETE' });
          if (r2.ok){ A.toast('Deleted.'); show('categories'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });
    }, 0);

    return html;
  };

  // ── Events ─────────────────────────────────────────────────────────────
  VIEWS.events = async function(){
    await Promise.all([
      adminCall('/categories').then(function(r){ if (r.ok) cache.categories = r.data.categories; }),
      adminCall('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }),
      fetchVenues(),
    ]);
    var rows = cache.events.map(function(e){
      var cat = cache.categories.filter(function(c){ return c.id === e.category_id; })[0];
      var ven = cache.venues.filter(function(v){ return v.id === e.venue_id; })[0];
      return '<tr>' +
        '<td>' + esc(e.code) + '</td>' +
        '<td>' + esc(e.title) + '</td>' +
        '<td>' + esc(cat ? cat.name : '—') + '</td>' +
        '<td>' + esc(ven ? ven.name : '—') + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td>' +
        '<td>' +
          '<button data-edit-e="' + e.id + '">Edit</button> ' +
          '<button class="danger" data-del-e="' + e.id + '">Delete</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    var html =
      '<div class="panel"><h2>Events (' + cache.events.length + ')</h2>' +
        '<table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th><th>When</th><th></th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="6" class="muted">none</td></tr>') + '</tbody></table>' +
      '</div>' +
      '<div class="panel"><h3>New event</h3>' +
        '<form id="event-form" class="row">' +
          '<input id="e-code" placeholder="Code" required style="width:8rem">' +
          '<input id="e-title" placeholder="Title" required style="flex:1;min-width:12rem">' +
          '<select id="e-cat"><option value="">— category —</option>' +
            cache.categories.map(function(c){ return '<option value="' + c.id + '">' + esc(c.name) + '</option>'; }).join('') +
          '</select>' +
          '<select id="e-venue"><option value="">— venue —</option>' +
            cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') +
          '</select>' +
          '<input id="e-day" placeholder="Day 1" style="width:6rem">' +
          '<input id="e-time" placeholder="09:00" style="width:6rem">' +
          '<button class="primary" type="submit">Add</button>' +
        '</form>' +
      '</div>';

    setTimeout(function(){
      var form = document.getElementById('event-form');
      if (form) form.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r = await adminCall('/events', { method: 'POST', body: {
          code: document.getElementById('e-code').value.trim(),
          title: document.getElementById('e-title').value.trim(),
          category_id: Number(document.getElementById('e-cat').value) || null,
          venue_id: Number(document.getElementById('e-venue').value) || null,
          day: document.getElementById('e-day').value.trim() || null,
          scheduled_time: document.getElementById('e-time').value.trim() || null,
        } });
        if (r.ok){ A.toast('Event created.'); show('events'); }
        else A.toast('Failed: ' + (r.detail || ''), true);
      });

      viewEl.querySelectorAll('[data-edit-e]').forEach(function(b){
        b.addEventListener('click', async function(){
          var id = Number(b.dataset.editE);
          var e = cache.events.filter(function(x){ return x.id === id; })[0];
          if (!e) return;
          var code = prompt('Code:', e.code); if (code == null) return;
          var title = prompt('Title:', e.title); if (title == null) return;
          var day = prompt('Day (blank = none):', e.day || ''); if (day == null) return;
          var time = prompt('Time (blank = none):', e.scheduled_time || ''); if (time == null) return;
          var r2 = await adminCall('/events/' + id, {
            method: 'PUT',
            body: {
              code: code.trim(),
              title: title.trim(),
              day: day.trim() || null,
              scheduled_time: time.trim() || null,
            },
          });
          if (r2.ok){ A.toast('Updated.'); show('events'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });

      viewEl.querySelectorAll('[data-del-e]').forEach(function(b){
        b.addEventListener('click', async function(){
          if (!confirm('Delete this event? All its participants must be removed first.')) return;
          var r2 = await adminCall('/events/' + b.dataset.delE, { method: 'DELETE' });
          if (r2.ok){ A.toast('Deleted.'); show('events'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });
    }, 0);

    return html;
  };

  // ── Queue ──────────────────────────────────────────────────────────────
  VIEWS.queue = async function(){
    await Promise.all([
      fetchVenues(),
      adminCall('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }),
    ]);

    var venueOpts = '<option value="">— select venue —</option>' + cache.venues.map(function(v){
      return '<option value="' + v.id + '">' + esc(v.name) + '</option>';
    }).join('');

    var eventOpts = '<option value="">— select event —</option>' + cache.events.map(function(e){
      return '<option value="' + e.id + '">' + esc(e.code) + ' · ' + esc(e.title) + '</option>';
    }).join('');

    var html =
      '<div class="panel"><h2>Add to Queue</h2>' +
        '<form id="queue-add" class="row">' +
          '<select id="q-venue" required style="flex:1">' + venueOpts + '</select>' +
          '<select id="q-event" required style="flex:2">' + eventOpts + '</select>' +
          '<input id="q-school" placeholder="School" required maxlength="200" style="flex:1">' +
          '<input id="q-name" placeholder="Student (optional)" maxlength="200" style="flex:1">' +
          '<input id="q-roll" placeholder="Roll (optional)" maxlength="64" style="width:8rem">' +
          '<button class="primary" type="submit">Add</button>' +
        '</form>' +
      '</div>' +
      '<div class="panel">' +
        '<div class="row" style="margin-bottom:.8rem">' +
          '<h2 style="margin:0">Queue</h2>' +
          '<span class="spacer" style="flex:1"></span>' +
          '<select id="q-filter"><option value="">All venues</option>' +
            cache.venues.map(function(v){ return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') +
          '</select>' +
          '<button id="q-refresh">Refresh</button>' +
        '</div>' +
        '<div id="queue-list"><p class="muted">Loading…</p></div>' +
      '</div>';

    setTimeout(async function(){
      var itemMap = {};

      async function loadList(venueId){
        var q = venueId ? ('?venue_id=' + venueId) : '';
        var r = await adminCall('/queue' + q);
        var listEl = document.getElementById('queue-list');
        if (!r.ok){ listEl.innerHTML = '<p class="muted">Failed.</p>'; return; }
        cache.queueItems = r.data.items;
        itemMap = {};
        cache.queueItems.forEach(function(it){ itemMap[it.id] = it; });

        if (!r.data.items.length){
          listEl.innerHTML = '<p class="muted">Empty.</p>';
          return;
        }

        var showMoves = !!venueId;
        var rows = r.data.items.map(function(i){
          return '<tr>' +
            '<td>' + (i.position + 1) + '</td>' +
            '<td>' + esc(i.event_code) + ' · ' + esc(i.event_title) + '</td>' +
            '<td>' + esc(i.school || '—') +
              '<br><span class="muted small">' + esc(i.student_name || '') + ' ' +
              (i.roll ? '· #' + esc(i.roll) : '') + '</span></td>' +
            '<td><span class="status ' + esc(i.status) + '">' + esc(i.status) + '</span></td>' +
            '<td>' +
              (['WAITING','COMPLETE'].indexOf(i.status) >= 0
                ? '<button data-edit-q="' + i.id + '">Edit</button> ' : '') +
              (i.status === 'WAITING'
                ? '<button class="danger" data-del="' + i.id + '">Delete</button>' : '') +
              (showMoves && i.status === 'WAITING'
                ? ' <button data-move="up" data-id="' + i.id + '" title="Move up">↑</button>' +
                  ' <button data-move="down" data-id="' + i.id + '" title="Move down">↓</button>'
                : '') +
            '</td>' +
          '</tr>';
        }).join('');

        listEl.innerHTML =
          '<table><thead><tr><th>#</th><th>Event</th><th>Participant</th><th>Status</th><th></th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table>';

        listEl.querySelectorAll('button[data-del]').forEach(function(b){
          b.addEventListener('click', async function(){
            if (!confirm('Delete this item?')) return;
            var res = await adminCall('/queue/' + b.dataset.del, { method: 'DELETE' });
            if (res.ok){ A.toast('Deleted.'); loadList(document.getElementById('q-filter').value); }
            else A.toast('Failed: ' + (res.detail || ''), true);
          });
        });

        listEl.querySelectorAll('button[data-move]').forEach(function(b){
          b.addEventListener('click', async function(){
            var res = await adminCall('/queue/' + b.dataset.id + '/move', {
              method: 'POST',
              body: { direction: b.dataset.move },
            });
            if (res.ok) loadList(document.getElementById('q-filter').value);
            else A.toast('Failed: ' + (res.detail || ''), true);
          });
        });

        listEl.querySelectorAll('button[data-edit-q]').forEach(function(b){
          b.addEventListener('click', async function(){
            var id = Number(b.dataset.editQ);
            var it = itemMap[id];
            if (!it) return;
            var school = prompt('School:', it.school || '');
            if (school == null) return;
            var name = prompt('Student name:', it.student_name || '');
            if (name == null) return;
            var roll = prompt('Roll number:', it.roll || '');
            if (roll == null) return;
            var res = await adminCall('/queue/' + id, {
              method: 'PUT',
              body: {
                school: school.trim(),
                student_name: name.trim() || null,
                roll: roll.trim() || null,
              },
            });
            if (res.ok){ A.toast('Saved.'); loadList(document.getElementById('q-filter').value); }
            else A.toast('Failed: ' + (res.detail || ''), true);
          });
        });
      }

      document.getElementById('queue-add').addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r2 = await adminCall('/queue', { method: 'POST', body: {
          venue_id: Number(document.getElementById('q-venue').value),
          event_id: Number(document.getElementById('q-event').value),
          school: document.getElementById('q-school').value.trim(),
          student_name: document.getElementById('q-name').value.trim() || null,
          roll: document.getElementById('q-roll').value.trim() || null,
        } });
        if (r2.ok){
          A.toast('Added.');
          document.getElementById('q-school').value = '';
          document.getElementById('q-name').value = '';
          document.getElementById('q-roll').value = '';
          loadList(document.getElementById('q-filter').value);
        } else A.toast('Failed: ' + (r2.detail || ''), true);
      });

      document.getElementById('q-filter').addEventListener('change', function(ev){
        loadList(ev.target.value);
      });
      document.getElementById('q-refresh').addEventListener('click', function(){
        loadList(document.getElementById('q-filter').value);
      });

      loadList('');
    }, 0);

    return html;
  };

  // ── Users ──────────────────────────────────────────────────────────────
  VIEWS.users = async function(){
    await fetchVenues();
    var r = await adminCall('/users');
    if (!r.ok) return '<div class="panel">Failed to load users.</div>';
    cache.users = r.data.users;

    var rows = cache.users.map(function(u){
      var stages = [];
      try {
        stages = JSON.parse(u.stages || '[]').map(function(id){
          var v = cache.venues.filter(function(x){ return x.id === id; })[0];
          return v ? v.name : ('#' + id);
        });
      } catch(e) {}
      var roleNames = (u.roles || []).join(', ') || '—';
      return '<tr>' +
        '<td>' + esc(u.email) + '</td>' +
        '<td>' + esc(roleNames) + '</td>' +
        '<td>' + esc(stages.join(', ') || '—') + '</td>' +
        '<td>' + (u.disabled ? '⛔ Disabled' : '✅ Active') + '</td>' +
        '<td>' +
          '<button data-edit-u="' + esc(u.id) + '">Edit</button> ' +
          (u.disabled
            ? '<button data-enable-u="' + esc(u.id) + '">Enable</button>'
            : '<button class="danger" data-dis="' + esc(u.id) + '">Disable</button>') +
        '</td>' +
      '</tr>';
    }).join('');

    var stageOpts = cache.venues.map(function(v){
      return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem 0 0">' +
        '<input type="checkbox" class="u-stage" value="' + v.id + '" style="width:auto;margin:0"> ' + esc(v.name) +
      '</label>';
    }).join('');

    var html =
      '<div class="panel"><h2>Staff accounts (' + cache.users.length + ')</h2>' +
        '<table><thead><tr><th>Email</th><th>Role</th><th>Stages</th><th>Status</th><th></th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table>' +
      '</div>' +
      '<div class="panel"><h3>New account</h3>' +
        '<form id="user-form" class="row">' +
          '<input id="u-email" type="email" placeholder="email@example.com" required style="flex:1">' +
          '<input id="u-pass" type="password" placeholder="password (12+)" required minlength="12" style="flex:1">' +
          '<select id="u-role"><option value="stagemaster">stagemaster</option><option value="admin">admin</option></select>' +
          '<button class="primary" type="submit">Create</button>' +
        '</form>' +
        '<p class="small muted" style="margin-top:.8rem">Assign stages:</p>' +
        '<div class="row">' + stageOpts + '</div>' +
      '</div>';

    setTimeout(function(){
      var form = document.getElementById('user-form');
      if (form) form.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var stages = Array.prototype.map.call(
          viewEl.querySelectorAll('.u-stage:checked'),
          function(x){ return Number(x.value); }
        );
        var email = document.getElementById('u-email').value.trim().toLowerCase();
        var r2 = await adminCall('/users', { method: 'POST', body: {
          email: email,
          role: document.getElementById('u-role').value,
          stages: stages,
          password: document.getElementById('u-pass').value,
        } });
        if (r2.ok){ A.toast('Created.'); show('users'); }
        else A.toast('Failed: ' + (r2.detail || ''), true);
      });

      viewEl.querySelectorAll('[data-dis]').forEach(function(b){
        b.addEventListener('click', async function(){
          if (!confirm('Disable this account?')) return;
          var r2 = await adminCall('/users/' + b.dataset.dis + '/disable', { method: 'POST' });
          if (r2.ok){ A.toast('Disabled.'); show('users'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });

      viewEl.querySelectorAll('[data-enable-u]').forEach(function(b){
        b.addEventListener('click', async function(){
          var r2 = await adminCall('/users/' + b.dataset.enableU + '/enable', { method: 'POST' });
          if (r2.ok){ A.toast('Enabled.'); show('users'); }
          else A.toast('Failed: ' + (r2.detail || ''), true);
        });
      });

      viewEl.querySelectorAll('[data-edit-u]').forEach(function(b){
        b.addEventListener('click', function(){
          openUserDialog(b.dataset.editU);
        });
      });
    }, 0);

    return html;
  };

  // ── User edit dialog helpers ───────────────────────────────────────────
  function openUserDialog(id){
    var u = cache.users.filter(function(x){ return x.id === id; })[0];
    if (!u) return;
    document.getElementById('u-edit-id').value = u.id;
    document.getElementById('u-edit-email').value = u.email;
    document.getElementById('u-edit-role').value = (u.roles && u.roles[0]) || 'stagemaster';
    document.getElementById('u-edit-active').value = u.disabled ? '0' : '1';

    var assigned = [];
    try { assigned = JSON.parse(u.stages || '[]'); } catch(e) {}
    var stageHtml = cache.venues.map(function(v){
      var checked = assigned.indexOf(v.id) >= 0;
      return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem .3rem 0">' +
        '<input type="checkbox" class="u-edit-stage" value="' + v.id + '"' +
          (checked ? ' checked' : '') + ' style="width:auto;margin:0"> ' + esc(v.name) +
      '</label>';
    }).join('');
    document.getElementById('u-edit-stages').innerHTML = stageHtml;
    document.getElementById('u-pass-id').value = u.id;
    document.getElementById('user-dialog').showModal();
  }

  function wireUserDialog(){
    var editForm = document.getElementById('user-edit-form');
    if (editForm) editForm.addEventListener('submit', async function(ev){
      ev.preventDefault();
      if (ev.submitter && ev.submitter.value !== 'save') return;
      var id = document.getElementById('u-edit-id').value;
      var stages = Array.prototype.map.call(
        document.querySelectorAll('.u-edit-stage:checked'),
        function(x){ return Number(x.value); }
      );
      var r = await adminCall('/users/' + id, { method: 'PUT', body: {
        email: document.getElementById('u-edit-email').value.trim().toLowerCase(),
        role: document.getElementById('u-edit-role').value,
        is_active: document.getElementById('u-edit-active').value === '1',
        stages: stages,
      } });
      if (r.ok){
        A.toast('Saved.');
        document.getElementById('user-dialog').close();
        show('users');
      } else A.toast('Failed: ' + (r.detail || ''), true);
    });

    var pwForm = document.getElementById('user-password-form');
    if (pwForm) pwForm.addEventListener('submit', async function(ev){
      ev.preventDefault();
      if (ev.submitter && ev.submitter.value !== 'save') return;
      var id = document.getElementById('u-pass-id').value;
      var pw = document.getElementById('u-pass-new').value;
      if (pw.length < 12){ A.toast('Password must be 12+ characters', true); return; }
      var r = await adminCall('/users/' + id + '/reset-password', {
        method: 'POST', body: { password: pw },
      });
      if (r.ok){
        A.toast('Password reset.');
        document.getElementById('u-pass-new').value = '';
        document.getElementById('user-dialog').close();
      } else A.toast('Failed: ' + (r.detail || ''), true);
    });

    document.querySelectorAll('[data-cancel-user]').forEach(function(b){
      b.addEventListener('click', function(){
        document.getElementById('user-dialog').close();
      });
    });
  }

  // ── Results / Leaderboard ─────────────────────────────────────────────
  VIEWS.results = async function(){
    var r = await adminCall('/leaderboard');
    if (!r.ok) return '<div class="panel">Failed to load leaderboard.</div>';

    var schoolRows = r.data.schools.map(function(s, idx){
      return '<tr>' +
        '<td>' + (idx + 1) + '</td>' +
        '<td>' + esc(s.school) + '</td>' +
        '<td>' + s.first + '</td>' +
        '<td>' + s.second + '</td>' +
        '<td>' + s.third + '</td>' +
        '<td><strong>' + s.total + '</strong></td>' +
      '</tr>';
    }).join('');

    var eventBlocks = r.data.events.map(function(e){
      var winners = e.winners.map(function(w){
        return '<li><strong>' + w.rank + '.</strong> ' +
          esc(w.school) + ' <span class="muted small">(' + w.total_score + ' pts avg)</span></li>';
      }).join('');
      return '<div class="panel"><h3>' + esc(e.event_code) + ' · ' + esc(e.event_title) + '</h3>' +
        '<ul style="margin:.4rem 0 0;padding-left:1.2rem">' + winners + '</ul></div>';
    }).join('');

    return (
      '<div class="panel"><h2>School Leaderboard</h2>' +
        '<p class="muted small">Points: 1st = 5, 2nd = 3, 3rd = 1 (Kerala School Kalolsavam standard).</p>' +
        '<table><thead><tr><th>Rank</th><th>School</th><th>1st</th><th>2nd</th><th>3rd</th><th>Total</th></tr></thead>' +
        '<tbody>' + (schoolRows || '<tr><td colspan="6" class="muted">No scored items yet.</td></tr>') + '</tbody></table>' +
      '</div>' +
      (eventBlocks || '<div class="panel"><p class="muted">No scored events yet.</p></div>')
    );
  };

  // ── Audit ──────────────────────────────────────────────────────────────
  VIEWS.audit = async function(){
    var r = await adminCall('/audit?limit=200');
    if (!r.ok) return '<div class="panel">Failed to load audit log.</div>';
    var rows = r.data.items.map(function(a){
      var ts = new Date((a.ts || 0) * 1000).toLocaleString();
      return '<tr>' +
        '<td class="small mono">' + esc(ts) + '</td>' +
        '<td>' + esc(a.username || '—') + '</td>' +
        '<td class="small mono">' + esc((a.ip_hash || '').slice(0, 10)) + '…</td>' +
        '<td>' + esc(a.event) + '</td>' +
        '<td class="small">' + esc(a.detail || '') + '</td>' +
      '</tr>';
    }).join('');
    return (
      '<div class="panel"><h2>Audit log (latest 200)</h2>' +
        '<table><thead><tr><th>Time</th><th>User</th><th>IP hash</th><th>Event</th><th>Detail</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table>' +
      '</div>'
    );
  };

  // ── Ops ────────────────────────────────────────────────────────────────
  VIEWS.ops = async function(){
    var [hr, sr] = await Promise.all([
      adminCall('/health'),
      adminCall('/stats'),
    ]);
    if (!hr.ok) return '<div class="panel">Health check failed.</div>';
    var h = hr.data;
    var st = sr.ok ? sr.data : {};

    var kv = '';
    var statLabels = {
      venues: 'Venues', categories: 'Categories', events: 'Events',
      participants: 'Participants', queue_items: 'Queue items',
      queue_waiting: 'Queue · waiting', queue_onstage: 'Queue · on stage',
      queue_complete: 'Queue · complete', scores_entered: 'Score entries',
    };
    Object.keys(statLabels).forEach(function(k){
      kv += '<span>' + statLabels[k] + '</span><b>' + (st[k] != null ? st[k] : '—') + '</b>';
    });

    return (
      '<div class="panel"><h2>Data</h2><div class="kv">' + kv + '</div></div>' +
      '<div class="panel"><h2>System</h2><div class="kv">' +
        '<span>DB size</span><b>' + (h.db_bytes/1024).toFixed(1) + ' KB</b>' +
        '<span>Disk free</span><b>' + (h.disk_free_bytes/1e9).toFixed(2) + ' GB</b>' +
        '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
        '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b>' +
      '</div></div>' +
      '<div class="panel"><h2>Operations</h2>' +
        '<div class="row" style="flex-wrap:wrap">' +
          '<button id="op-backup" class="primary">💾 Backup databases</button>' +
          '<a class="button" href="/api/v1/admin/export/participants.csv" download style="display:inline-flex;align-items:center;padding:.5rem .9rem;border:1px solid var(--border);border-radius:6px;background:var(--panel-2);color:var(--text);text-decoration:none">⬇ Participants CSV</a>' +
          '<a class="button" href="/api/v1/admin/export/results.csv" download style="display:inline-flex;align-items:center;padding:.5rem .9rem;border:1px solid var(--border);border-radius:6px;background:var(--panel-2);color:var(--text);text-decoration:none">⬇ Results CSV</a>' +
        '</div>' +
      '</div>'
    );
  };

  function wireOpsHandlers(){
    var backupBtn = document.getElementById('op-backup');
    if (backupBtn) backupBtn.addEventListener('click', async function(){
      var r = await adminCall('/backup', { method: 'POST' });
      if (r.ok) A.toast('Backup saved.');
      else A.toast('Backup failed', true);
    });
  }

  // ── Login handler ──────────────────────────────────────────────────────
  window.onKalLogin = function(info){
    var role = String(info.role || '').toLowerCase();
    if (role !== 'admin'){
      document.getElementById('login-msg').textContent = 'Admin console only. Sign out and use an admin account.';
      return;
    }
    document.body.classList.remove('login-body');
    var loginCard = document.querySelector('.login-card');
    if (loginCard) loginCard.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent =
      (info.email || info.username || 'admin') + ' · admin';
    show('venues');
  };

  // ── Boot ───────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function(){
    viewEl = document.getElementById('view');
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('tabs').addEventListener('click', function(ev){
      var t = ev.target.closest('.tab');
      if (t) show(t.dataset.tab);
    });

    // Wire up dialogs and global buttons
    wireUserDialog();
    wireOpsHandlers();

    // Wrap show() so ops handlers are re-wired after every render
    var _origShow = show;
    show = function(tab){
      _origShow(tab);
      if (tab === 'ops') {
        setTimeout(wireOpsHandlers, 50);
      }
    };

    window.KalAuth.init();
  });
})();
