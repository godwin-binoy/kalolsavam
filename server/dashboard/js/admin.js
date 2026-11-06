(function(){
  'use strict';
  var A = window.KalAPI;
  var viewEl;
  var cache = { venues: [], categories: [], events: [] };

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  function askStepUp(what){
    return new Promise(function(resolve){
      var dlg = document.getElementById('stepup-dialog');
      var form = document.getElementById('stepup-form');
      document.getElementById('stepup-what').textContent = what;
      document.getElementById('stepup-code').value = '';
      delete form.dataset.cancelled;
      dlg.showModal();
      function done(ev){
        ev.preventDefault();
        var cancelled = form.dataset.cancelled === '1';
        var code = document.getElementById('stepup-code').value.trim();
        dlg.close();
        form.removeEventListener('submit', done);
        dlg.removeEventListener('close', onclose);
        resolve(!cancelled && /^\d{6}$/.test(code) ? code : null);
      }
      function onclose(){
        form.removeEventListener('submit', done);
        dlg.removeEventListener('close', onclose);
        resolve(null);
      }
      form.addEventListener('submit', done);
      dlg.addEventListener('close', onclose);
    });
  }

  async function adminCall(path, opts, stepUpWhat){
    opts = opts || {};
    opts.headers = opts.headers || {};
    if (stepUpWhat){
      var code = await askStepUp(stepUpWhat);
      if (!code) return { ok: false, detail: 'cancelled' };
      opts.headers['x-step-up-totp'] = code;
    }
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

  VIEWS.venues = async function(){
    var vs = await fetchVenues();
    var rows = vs.map(function(v){
      return '<tr><td>' + v.id + '</td><td>' + esc(v.name) + '</td><td>' + esc(v.kind) +
        '</td><td>' + (v.active ? '✅' : '⛔') + '</td></tr>';
    }).join('');
    var html = '<div class="panel"><h2>Venues (' + vs.length + ')</h2>' +
      '<table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Active</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="4" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New venue</h3><form id="venue-form" class="row">' +
      '<input id="v-name" placeholder="Name" required maxlength="120" style="flex:1">' +
      '<select id="v-kind"><option>stage</option><option>room</option><option>hall</option><option>ground</option></select>' +
      '<button class="primary" type="submit">Add</button></form></div>';
    setTimeout(function(){
      document.getElementById('venue-form').addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r = await adminCall('/venues', { method: 'POST', body: {
          name: document.getElementById('v-name').value.trim(),
          kind: document.getElementById('v-kind').value, active: true } });
        if (r.ok){ A.toast('Venue created.'); show('venues'); }
        else A.toast('Failed: ' + (r.detail || ''), true);
      });
    }, 0);
    return html;
  };

  VIEWS.events = async function(){
    await Promise.all([
      adminCall('/categories').then(function(r){ if (r.ok) cache.categories = r.data.categories; }),
      adminCall('/events').then(function(r){ if (r.ok) cache.events = r.data.events; }),
      fetchVenues()
    ]);
    var rows = cache.events.map(function(e){
      var cat = cache.categories.filter(function(c){ return c.id === e.category_id; })[0];
      var ven = cache.venues.filter(function(v){ return v.id === e.venue_id; })[0];
      return '<tr><td>' + esc(e.code) + '</td><td>' + esc(e.title) + '</td>' +
        '<td>' + esc(cat ? cat.name : '—') + '</td>' +
        '<td>' + esc(ven ? ven.name : '—') + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td></tr>';
    }).join('');
    var html = '<div class="panel"><h2>Events (' + cache.events.length + ')</h2>' +
      '<table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th><th>When</th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New event</h3><form id="event-form" class="row">' +
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
      '<button class="primary" type="submit">Add</button></form></div>';
    setTimeout(function(){
      document.getElementById('event-form').addEventListener('submit', async function(ev){
        ev.preventDefault();
        var r = await adminCall('/events', { method: 'POST', body: {
          code: document.getElementById('e-code').value.trim(),
          title: document.getElementById('e-title').value.trim(),
          category_id: Number(document.getElementById('e-cat').value) || null,
          venue_id: Number(document.getElementById('e-venue').value) || null,
          day: document.getElementById('e-day').value.trim() || null,
          scheduled_time: document.getElementById('e-time').value.trim() || null } });
        if (r.ok){ A.toast('Event created.'); show('events'); }
        else A.toast('Failed: ' + (r.detail || ''), true);
      });
    }, 0);
    return html;
  };

  VIEWS.users = async function(){
    await fetchVenues();
    var r = await adminCall('/users');
    if (!r.ok) return '<div class="panel">Failed to load users.</div>';
    var rows = r.data.users.map(function(u){
      var stages = JSON.parse(u.stages || '[]').map(function(id){
        var v = cache.venues.filter(function(x){ return x.id === id; })[0];
        return v ? v.name : id;
      }).join(', ');
      return '<tr><td>' + u.id + '</td><td>' + esc(u.username) + '</td><td>' + esc(u.role) +
        '</td><td>' + esc(stages || '—') + '</td>' +
        '<td>' + (u.totp_required ? '🔐' : '—') + '</td>' +
        '<td>' + (u.disabled ? '⛔' : '✅') + '</td>' +
        '<td><button data-dis="' + u.id + '" data-name="' + esc(u.username) + '"' +
        (u.disabled ? ' disabled' : '') + '>Disable</button></td></tr>';
    }).join('');
    var stageOpts = cache.venues.map(function(v){
      return '<label class="small" style="display:inline-flex;gap:.3rem;align-items:center;margin:0 .6rem 0 0">' +
        '<input type="checkbox" class="u-stage" value="' + v.id + '" style="width:auto;margin:0"> ' + esc(v.name) + '</label>';
    }).join('');
    var html = '<div class="panel"><h2>Staff accounts</h2>' +
      '<table><thead><tr><th>ID</th><th>User</th><th>Role</th><th>Stages</th><th>TOTP</th><th>Status</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="7" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New account</h3><form id="user-form" class="row">' +
      '<input id="u-name" placeholder="username" required pattern="[a-z0-9._-]{3,64}" style="flex:1">' +
      '<input id="u-pass" type="password" placeholder="password (12+)" required minlength="12" style="flex:1">' +
      '<select id="u-role"><option value="stagemaster">stagemaster</option><option value="admin">admin</option></select>' +
      '<button class="primary" type="submit">Create</button></form>' +
      '<p class="small muted" style="margin-top:.8rem">Assign stages:</p><div class="row">' + stageOpts + '</div></div>';
    setTimeout(function(){
      document.getElementById('user-form').addEventListener('submit', async function(ev){
        ev.preventDefault();
        var stages = Array.prototype.map.call(
          viewEl.querySelectorAll('.u-stage:checked'), function(x){ return Number(x.value); });
        var r = await adminCall('/users', { method: 'POST', body: {
          username: document.getElementById('u-name').value.trim().toLowerCase(),
          role: document.getElementById('u-role').value,
          stages: stages,
          password: document.getElementById('u-pass').value } });
        if (r.ok){ A.toast('Created.'); show('users'); }
        else A.toast('Failed: ' + (r.detail || ''), true);
      });
      viewEl.querySelectorAll('button[data-dis]').forEach(function(b){
        b.addEventListener('click', async function(){
          var r = await adminCall('/users/' + b.dataset.dis + '/disable',
            { method: 'POST' }, 'Disable ' + b.dataset.name + '? Enter TOTP:');
          if (r.ok){ A.toast('Disabled.'); show('users'); }
        });
      });
    }, 0);
    return html;
  };

  VIEWS.ops = async function(){
    var r = await adminCall('/health');
    if (!r.ok) return '<div class="panel">Health check failed.</div>';
    var h = r.data;
    return '<div class="panel"><h2>System</h2><div class="kv">' +
      '<span>Active sessions</span><b>' + h.active_sessions + '</b>' +
      '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
      '<span>DB size</span><b>' + (h.db_bytes/1024).toFixed(1) + ' KB</b>' +
      '<span>Disk free</span><b>' + (h.disk_free_bytes/1e9).toFixed(2) + ' GB</b>' +
      '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b>' +
      '</div><div class="row" style="margin-top:.8rem">' +
      '<button id="op-backup">🔒 Backup DB</button></div></div>';
  };

  document.addEventListener('click', async function(ev){
    var b = ev.target.closest ? ev.target.closest('button') : null;
    if (!b) return;
    if (b.id === 'op-backup'){
      var r = await adminCall('/backup', { method: 'POST' }, 'Run DB backup. Enter TOTP:');
      if (r.ok) A.toast('Backup: ' + r.data.path);
    }
  });

  window.onKalLogin = function(info){
    if (info.role !== 'admin'){
      document.getElementById('login-msg').textContent = 'Admin console only.';
      return;
    }
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent = info.username + ' · admin';
    show('venues');
  };

  document.addEventListener('DOMContentLoaded', function(){
    viewEl = document.getElementById('view');
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('tabs').addEventListener('click', function(ev){
      var t = ev.target.closest('.tab');
      if (t) show(t.dataset.tab);
    });
    window.KalAuth.init();
  });
})();
