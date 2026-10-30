/* Admin console ("manage") UI: master data CRUD, users, sessions, audit and
 * ops. Every action hits /api/admin/* which is role+IP gated server-side;
 * destructive actions additionally require a live TOTP (step-up dialog). */
(function () {
  'use strict';
  var A = window.KalAPI;

  var viewEl, connEl, whoEl;
  var current = 'dashboard';
  var cache = { venues: [], categories: [], events: [] };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtTs(t) {
    if (!t) return '—';
    return new Date(t * 1000).toLocaleString();
  }

  /* ---------------------------------------------------- step-up helper -- */
  function askStepUp(what) {
    return new Promise(function (resolve) {
      var dlg = document.getElementById('stepup-dialog');
      document.getElementById('stepup-what').textContent = what;
      document.getElementById('stepup-code').value = '';
      dlg.showModal();
      var form = document.getElementById('stepup-form');
      function done(ev) {
        ev.preventDefault();
        var btn = form.querySelector('button[value=go]');
        var code = document.getElementById('stepup-code').value.trim();
        dlg.close();
        form.removeEventListener('submit', done);
        resolve(btn && /^\d{6}$/.test(code) ? code : null);
      }
      form.addEventListener('submit', done);
    });
  }

  async function adminCall(path, opts, stepUpWhat) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    if (stepUpWhat) {
      var code = await askStepUp(stepUpWhat);
      if (!code) return { ok: false, detail: 'cancelled' };
      opts.headers['x-step-up-totp'] = code;
    }
    var r = await A.api('/api/admin' + path, opts);
    if (r.status === 403 && r.detail === 'forbidden_network') {
      A.toast('This API is restricted to the staff network (IP allowlist).', true);
    } else if (r.status === 403 && r.detail === 'stepup_failed') {
      A.toast('Step-up code rejected.', true);
    } else if (!r.ok && r.detail !== 'cancelled') {
      A.toast('Request failed: ' + (r.detail || r.status), true);
    }
    return r;
  }

  /* ------------------------------------------------------------- tabs --- */
  var VIEWS = {};

  function show(tab) {
    current = tab;
    document.querySelectorAll('.tab').forEach(function (b) {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    viewEl.innerHTML = '<div class="panel"><p class="muted">Loading…</p></div>';
    VIEWS[tab]().then(function (html) { viewEl.innerHTML = html; });
  }

  /* -------------------------------------------------------- dashboard --- */
  VIEWS.dashboard = async function () {
    var r = await adminCall('/health');
    if (!r.ok) return '<div class="panel"><p class="muted err">Health check failed.</p></div>';
    var h = r.data;
    var gb = function (n) { return (n / 1e9).toFixed(2) + ' GB'; };
    return '<div class="panel"><h2>System health</h2><div class="kv">' +
      '<span>Server time</span><b>' + fmtTs(h.time) + '</b>' +
      '<span>SSE connections</span><b>' + h.sse_connections + '</b>' +
      '<span>Active sessions</span><b>' + h.active_sessions + '</b>' +
      '<span>DB size</span><b>' + gb(h.db_bytes) + '</b>' +
      '<span>Disk free</span><b>' + gb(h.disk_free_bytes) + '</b>' +
      '<span>Load avg</span><b>' + h.load_avg.map(function (x) { return Number(x).toFixed(2); }).join(' ') + '</b>' +
      '<span>Audit chain</span><b style="color:' + (h.audit_chain.valid ? 'var(--ok)' : 'var(--err)') + '">' +
        (h.audit_chain.valid ? 'VALID' : 'BROKEN!!') + ' (' + h.audit_chain.entries + ' entries)</b>' +
      '<span>Auth failures (1h)</span><b>' + h.recent_auth_failures + '</b>' +
      '</div><div class="row" style="margin-top:.8rem"><button id="recheck">Re-check</button></div></div>';
  };

  /* ----------------------------------------------------------- venues --- */
  async function fetchVenues() {
    var r = await adminCall('/venues');
    cache.venues = r.ok ? r.data.venues : [];
    return cache.venues;
  }

  VIEWS.venues = async function () {
    var vs = await fetchVenues();
    var rows = vs.map(function (v) {
      return '<tr><td>' + v.id + '</td><td>' + esc(v.name) + '</td><td>' + esc(v.kind) +
        '</td><td>' + (v.active ? '✅ active' : '⛔ inactive') + '</td>' +
        '<td class="row"><button data-edit="' + v.id + '">Edit</button></td></tr>';
    }).join('');
    var html = '<div class="panel"><h2>Venues / stages</h2>' +
      '<table><thead><tr><th>ID</th><th>Name</th><th>Kind</th><th>Active</th><th></th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>' +
      '<div class="panel"><h3>New venue</h3><form id="venue-form" class="row">' +
      '<input id="v-name" placeholder="Name" required maxlength="120" style="flex:1">' +
      '<select id="v-kind"><option>stage</option><option>room</option><option>hall</option><option>ground</option></select>' +
      '<button class="primary" type="submit">Add venue</button></form></div>';
    setTimeout(function () {
      document.getElementById('venue-form').addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var r = await adminCall('/venues', { method: 'POST', body: {
          name: document.getElementById('v-name').value.trim(),
          kind: document.getElementById('v-kind').value, active: true } });
        if (r.ok) { A.toast('Venue created.'); show('venues'); }
      });
      viewEl.querySelectorAll('button[data-edit]').forEach(function (b) {
        b.addEventListener('click', function () {
          var v = cache.venues.filter(function (x) { return x.id === Number(b.dataset.edit); })[0];
          var name = prompt('Venue name:', v.name);
          if (name === null) return;
          var active = confirm('Active?');
          adminCall('/venues/' + v.id, { method: 'PATCH', body: {
            name: name.trim() || v.name, kind: v.kind, active: active } })
            .then(function (r) { if (r.ok) { A.toast('Venue updated.'); show('venues'); } });
        });
      });
      var rb = document.getElementById('recheck');
      if (rb) rb.addEventListener('click', function () { show('dashboard'); });
    }, 0);
    return html;
  };

  /* ----------------------------------------------------------- events --- */
  async function fetchMaster() {
    var rs = await Promise.all([adminCall('/categories'), adminCall('/events')]);
    if (rs[0].ok) cache.categories = rs[0].data.categories;
    if (rs[1].ok) cache.events = rs[1].data.events;
    return rs;
  }

  VIEWS.events = async function () {
    await fetchMaster();
    var vopts = cache.venues.length ? cache.venues : await fetchVenues();
    var rows = cache.events.map(function (e) {
      return '<tr><td>' + esc(e.code) + '</td><td>' + esc(e.title) + '</td>' +
        '<td>' + esc(catName(e.category_id)) + '</td><td>' + esc(venueName(e.venue_id)) + '</td>' +
        '<td>' + esc(e.day || '') + ' ' + esc(e.scheduled_time || '') + '</td>' +
        '<td class="row"><button data-q="' + e.id + '">Build queue</button></td></tr>';
    }).join('');
    var html = '<div class="panel"><h2>Events (' + cache.events.length + ')</h2>' +
      '<table><thead><tr><th>Code</th><th>Title</th><th>Category</th><th>Venue</th>' +
      '<th>When</th><th></th></tr></thead><tbody>' + (rows ||
      '<tr><td colspan="6" class="muted">No events yet.</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h3>New event</h3><form id="event-form" class="row">' +
      '<input id="e-code" placeholder="Code (e.g. M-01)" required style="width:9rem">' +
      '<input id="e-title" placeholder="Title" required style="flex:1;min-width:12rem">' +
      '<select id="e-cat">' + cache.categories.map(function (c) {
        return '<option value="' + c.id + '">' + esc(c.name) + '</option>'; }).join('') + '</select>' +
      '<select id="e-venue">' + vopts.map(function (v) {
        return '<option value="' + v.id + '">' + esc(v.name) + '</option>'; }).join('') + '</select>' +
      '<input id="e-day" placeholder="Day 1" style="width:7rem">' +
      '<input id="e-time" placeholder="09:00" style="width:7rem">' +
      '<button class="primary" type="submit">Add event</button></form></div>';
    setTimeout(function () {
      document.getElementById('event-form').addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var r = await adminCall('/events', { method: 'POST', body: {
          code: document.getElementById('e-code').value.trim(),
          title: document.getElementById('e-title').value.trim(),
          category_id: Number(document.getElementById('e-cat').value) || null,
          venue_id: Number(document.getElementById('e-venue').value) || null,
          day: document.getElementById('e-day').value.trim() || null,
          scheduled_time: document.getElementById('e-time').value.trim() || null } });
        if (r.ok) { A.toast('Event created (#' + r.data.id + ').'); show('events'); }
      });
      viewEl.querySelectorAll('button[data-q]').forEach(function (b) {
        b.addEventListener('click', async function () {
          var r = await adminCall('/events/build-queue', { method: 'POST',
            body: { event_id: Number(b.dataset.q) } });
          if (r.ok) A.toast('Queue built: ' + r.data.created + ' items.');
        });
      });
    }, 0);
    return html;
  };
  function catName(id) { var c = cache.categories.filter(function (x) { return x.id === id; })[0]; return c ? c.name : '—'; }
  function venueName(id) { var v = cache.venues.filter(function (x) { return x.id === id; })[0]; return v ? v.name : '—'; }

  /* ------------------------------------------------------------ users --- */
  VIEWS.users = async function () {
    await fetchVenues();
    var r = await adminCall('/users');
    if (!r.ok) return '<div class="panel">Failed to load users.</div>';
    var rows = r.data.users.map(function (u) {
      var stages = JSON.parse(u.stages || '[]').map(venueName).join(', ');
      return '<tr><td>' + u.id + '</td><td>' + esc(u.username) + '</td><td>' + esc(u.role) +
        '</td><td>' + esc(stages || '—') + '</td>' +
        '<td>' + (u.totp_required ? '🔐' : '—') + '</td>' +
        '<td>' + (u.disabled ? '⛔ disabled' : '✅') + '</td>' +
        '<td class="row"><button data-dis="' + u.id + '" data-name="' + esc(u.username) + '"' +
        (u.disabled ? ' disabled' : '') + '>Disable</button></td></tr>';
    }).join('');
    var stageOpts = cache.venues.map(function (v) {
      return '<label class="small"><input type="checkbox" class="u-stage" value="' + v.id + '"> ' + esc(v.name) + '</label>';
    }).join(' ');
    var html = '<div class="panel"><h2>Staff accounts</h2>' +
      '<table><thead><tr><th>ID</th><th>User</th><th>Role</th><th>Stages</th><th>TOTP</th>' +
      '<th>Status</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="panel"><h3>New stagemaster / admin account</h3>' +
      '<form id="user-form" class="row">' +
      '<input id="u-name" placeholder="username (lowercase)" required pattern="[a-z0-9._-]{3,64}" style="flex:1">' +
      '<select id="u-role"><option value="stagemaster">stagemaster</option><option value="admin">admin</option></select>' +
      '<button class="primary" type="submit">Create</button></form>' +
      '<p class="small muted" id="u-stages-label">Assigned stages:</p><div class="row">' + stageOpts + '</div>' +
      '<p class="small muted">A one-time password is shown exactly once after creation — deliver it in person.</p></div>';
    setTimeout(function () {
      document.getElementById('user-form').addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var stages = Array.prototype.map.call(
          viewEl.querySelectorAll('.u-stage:checked'), function (x) { return Number(x.value); });
        var r = await adminCall('/users', { method: 'POST', body: {
          username: document.getElementById('u-name').value.trim().toLowerCase(),
          role: document.getElementById('u-role').value, stages: stages } });
        if (r.ok) {
          alert('Account created.\n\nOne-time password (show once, deliver in person):\n\n' +
                r.data.one_time_password);
          show('users');
        }
      });
      viewEl.querySelectorAll('button[data-dis]').forEach(function (b) {
        b.addEventListener('click', async function () {
          var r = await adminCall('/users/' + b.dataset.dis + '/disable', { method: 'POST' },
            'Disabling "' + b.dataset.name + '" revokes all their sessions. Enter your TOTP:');
          if (r.ok) { A.toast('User disabled.'); show('users'); }
        });
      });
    }, 0);
    return html;
  };

  /* --------------------------------------------------------- sessions --- */
  VIEWS.sessions = async function () {
    var r = await adminCall('/sessions');
    if (!r.ok) return '<div class="panel">Failed to load sessions.</div>';
    var rows = r.data.sessions.map(function (s) {
      return '<tr><td>' + esc(s.username) + '</td><td>' + esc(s.role) + '</td>' +
        '<td>' + fmtTs(s.created_at) + '</td><td>' + fmtTs(s.last_seen) + '</td>' +
        '<td>' + (s.revoked ? 'revoked' : '<b>active</b>') + '</td></tr>';
    }).join('');
    var html = '<div class="panel"><h2>Active sessions</h2>' +
      '<div class="toolbar"><button id="revoke-all" class="danger">Revoke ALL sessions</button></div>' +
      '<table><thead><tr><th>User</th><th>Role</th><th>Started</th><th>Last seen</th>' +
      '<th>Status</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    setTimeout(function () {
      document.getElementById('revoke-all').addEventListener('click', async function () {
        var r = await adminCall('/sessions/revoke-all', { method: 'POST' },
          'This signs every staff member out immediately. Enter your TOTP:');
        if (r.ok) { A.toast('All sessions revoked.'); show('sessions'); }
      });
    }, 0);
    return html;
  };

  /* ------------------------------------------------------------ audit --- */
  VIEWS.audit = async function () {
    var rs = await Promise.all([adminCall('/audit/admin?limit=200'),
                                adminCall('/audit/auth?limit=200')]);
    var adm = rs[0].ok ? rs[0].data : { actions: [], chain_valid: false };
    var auth = rs[1].ok ? rs[1].data : { events: [] };
    var arows = adm.actions.map(function (a) {
      return '<tr><td>' + fmtTs(a.ts) + '</td><td>' + esc(a.actor || '') + '</td>' +
        '<td>' + esc(a.action) + '</td><td>' + esc(a.target || '') + '</td></tr>';
    }).join('');
    var frows = auth.events.map(function (e) {
      return '<tr><td>' + fmtTs(e.ts) + '</td><td>' + esc(e.username || '') + '</td>' +
        '<td>' + esc(e.event) + '</td><td>' + esc(e.ip || '') + '</td>' +
        '<td class="small muted">' + esc(e.detail || '') + '</td></tr>';
    }).join('');
    return '<div class="panel"><h2>Admin actions (hash-chained) ' +
      (adm.chain_valid ? '<span class="badge live">chain valid</span>'
                       : '<span class="badge offline">CHAIN BROKEN</span>') + '</h2>' +
      '<table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead>' +
      '<tbody>' + (arows || '<tr><td colspan="4" class="muted">none</td></tr>') + '</tbody></table></div>' +
      '<div class="panel"><h2>Authentication log</h2>' +
      '<table><thead><tr><th>Time</th><th>User</th><th>Event</th><th>IP</th><th>Detail</th></tr></thead>' +
      '<tbody>' + (frows || '<tr><td colspan="5" class="muted">none</td></tr>') + '</tbody></table></div>';
  };

  /* -------------------------------------------------------------- ops --- */
  VIEWS.ops = async function () {
    var r = await adminCall('/flags');
    var flags = r.ok ? r.data.flags : {};
    var frows = Object.keys(flags).map(function (k) {
      return '<tr><td><code>' + esc(k) + '</code></td><td>' + esc(flags[k]) + '</td></tr>';
    }).join('');
    return '<div class="panel"><h2>Operations</h2><div class="row">' +
      '<button id="op-backup">Run DB backup 🔒</button>' +
      '<button id="op-deploy">Rebuild public site 🔒</button>' +
      '</div><p class="small muted">🔒 actions require a fresh TOTP (step-up).</p></div>' +
      '<div class="panel"><h2>Feature flags</h2>' +
      '<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>' +
      (frows || '<tr><td colspan="2" class="muted">no flags</td></tr>') + '</tbody></table>' +
      '<form id="flag-form" class="row" style="margin-top:.8rem">' +
      '<input id="f-key" placeholder="key" required pattern="[a-z0-9_.]{1,64}" style="width:12rem">' +
      '<input id="f-val" placeholder="value" maxlength="256" style="flex:1">' +
      '<button class="primary" type="submit">Set flag 🔒</button></form></div>';
  };

  // ops buttons are wired via delegation because the view re-renders
  document.addEventListener('click', async function (ev) {
    var b = ev.target.closest ? ev.target.closest('button') : null;
    if (!b) return;
    if (b.id === 'op-backup') {
      var r = await adminCall('/backup', { method: 'POST' },
        'Running a database backup. Enter your TOTP:');
      if (r.ok) A.toast('Backup written: ' + r.data.path);
    }
    if (b.id === 'op-deploy') {
      var r2 = await adminCall('/deploy', { method: 'POST' },
        'Rebuilding + deploying the public site snapshot. Enter your TOTP:');
      if (r2.ok) A.toast('Public site rebuilt.');
    }
  });

  /* ----------------------------------------------------------- boot ----- */
  window.onKalLogin = function (info) {
    if (info.role !== 'admin') {
      document.getElementById('login-msg').textContent =
        'This console is for administrators only.';
      return;
    }
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    whoEl.textContent = info.username + ' · admin';
    connEl.textContent = 'authenticated';
    connEl.className = 'badge live';
    show(current);
  };

  document.addEventListener('DOMContentLoaded', function () {
    viewEl = document.getElementById('view');
    connEl = document.getElementById('conn');
    whoEl = document.getElementById('who');
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('tabs').addEventListener('click', function (ev) {
      var t = ev.target.closest('.tab');
      if (t) show(t.dataset.tab);
    });
    // flag form submit (delegated since view re-renders)
    document.addEventListener('submit', function (ev) {
      if (ev.target.id !== 'flag-form') return;
      ev.preventDefault();
      adminCall('/flags', { method: 'POST', body: {
        key: document.getElementById('f-key').value.trim(),
        value: document.getElementById('f-val').value } },
        'Writing feature flag. Enter your TOTP:')
        .then(function (r) { if (r.ok) { A.toast('Flag set.'); show('ops'); } });
    });
    window.KalAuth.init();
  });
})();
