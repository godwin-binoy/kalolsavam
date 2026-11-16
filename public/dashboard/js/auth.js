/* Shared portal shell renderer + auth, session resume, theme toggle, password modal, CSV downloads. */
(function () {
  'use strict';

  var A = window.KalAPI, el = A.el;
  var msgEl, formEl, btnEl;

  function mountShell() {
    var portal = document.body.dataset.portal;
    var app = el('app');
    if (!portal || !app || document.querySelector('.login-card')) return;

    var cfg = {
      admin: {
        badge: 'Admin Console',
        sub: 'Stages, events, participants, staff accounts, and operations.',
        topBadge: 'Admin',
        extra: '<a href="/dashboard/" class="btn-link">📊 Dashboard</a><a href="/dataworker/" class="btn-link">📷 Data Worker</a>'
      },
      stagemaster: {
        badge: 'Stage Control',
        sub: 'Staff sign-in. Only assigned stages are accessible.',
        topBadge: 'Stage Control',
        extra: '<span id="conn" class="badge">connecting…</span><span class="spacer"></span><button id="theme" title="Toggle dark mode" style="margin-right:.5rem">🌓 Theme</button><button id="change-pass-btn" class="small">🔑 Password</button><button id="sync-btn">↻ Sync</button>'
      },
      dataworker: {
        badge: 'Data Worker',
        sub: 'Match slip photos to participants and publish stage photos.',
        topBadge: 'Data Worker',
        extra: '<span class="spacer"></span><button id="theme" title="Toggle dark mode" style="margin-right:.5rem">🌓 Theme</button><button id="change-pass-btn" class="small">🔑 Password</button><button id="refresh-batches-btn">↻ Refresh</button>'
      }
    }[portal];
    if (!cfg) return;

    var loginCard = document.createElement('main');
    loginCard.className = 'login-card';
    loginCard.innerHTML =
      '<h1 class="brand">Kalolsavam <span>' + cfg.badge + '</span></h1>' +
      '<p class="muted small">' + cfg.sub + '</p>' +
      '<form id="login-form" autocomplete="off">' +
        '<label>Email<input id="email" type="email" required maxlength="120" autocomplete="email"></label>' +
        '<label>Password<input id="password" type="password" required autocomplete="current-password"></label>' +
        '<button type="submit" id="login-btn">Sign in</button>' +
        '<p id="login-msg" class="msg" role="status" aria-live="polite"></p>' +
      '</form>';
    document.body.insertBefore(loginCard, app);

    var hdr = document.createElement('header');
    hdr.className = 'topbar';
    hdr.innerHTML = portal === 'admin'
      ? '<h1 class="brand">Kalolsavam <span>' + cfg.topBadge + '</span></h1><span id="who" class="badge"></span><span class="spacer"></span><button id="theme" title="Toggle dark mode" style="margin-right:.5rem">🌓 Theme</button><button id="change-pass-btn" class="small">🔑 Password</button>' + cfg.extra + '<button id="logout-btn">Sign out</button>'
      : '<h1 class="brand">Kalolsavam <span>' + cfg.topBadge + '</span></h1><span id="who" class="badge"></span>' + cfg.extra + '<button id="logout-btn">Sign out</button>';
    app.insertBefore(hdr, app.firstChild);

    if (!el('self-password-dialog')) {
      var dlg = document.createElement('dialog');
      dlg.id = 'self-password-dialog';
      dlg.innerHTML =
        '<h3 style="margin-top:0">Change My Password</h3>' +
        '<form id="self-password-form">' +
          '<label>Current password<input id="self-old-pass" type="password" required autocomplete="current-password"></label>' +
          '<label>New password (12+ characters)<input id="self-new-pass" type="password" minlength="12" required autocomplete="new-password"></label>' +
          '<div class="row" style="margin-top:.9rem"><button class="primary" type="submit">Update Password</button><button type="button" data-cancel-self-pass>Cancel</button></div>' +
        '</form>';
      document.body.appendChild(dlg);
    }
  }
  mountShell();

  function msg(text, cls) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }
  function storeUser(payload) { try { sessionStorage.setItem('kal_user', JSON.stringify(payload)); } catch (e) {} }
  function dropUser() { try { sessionStorage.removeItem('kal_user'); } catch (e) {} }

  function buildPayload(info) {
    info = info || {};
    var roles = Array.isArray(info.roles) ? info.roles : [];
    var first = roles[0];
    var role = (first && (first.name || first)) || info.role || '';
    var name = info.email || info.username || '';
    return { username: name, email: name, role: role, roles: roles, stages: info.stages || [] };
  }

  async function login(username, password) {
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var r = await fetch(A.url('/api/v1/auth/login'), {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: username, password: password })
      });
      var v = await r.json().catch(function () { return {}; });
      if (!r.ok) {
        var why = (v && (v.error || v.detail)) || ('Sign-in failed (' + r.status + ').');
        msg(typeof why === 'string' ? why : 'Sign-in failed.', 'err');
        return false;
      }
      if (v.access_token) A.setToken(v.access_token);
      if (v.refresh_token) A.setRefreshToken(v.refresh_token);
      var me = await A.api('/api/v1/auth/me');
      var payload = buildPayload(me.ok ? me.data : (v.user || v));
      storeUser(payload);
      msg('Signed in as ' + (payload.username || 'user') + '.', 'ok');
      if (window.onKalLogin) window.onKalLogin(payload);
      return true;
    } catch (e) {
      msg('Network error: ' + e.message, 'err');
      return false;
    } finally {
      btnEl.disabled = false;
    }
  }

  async function logout() {
    var rf = A.getRefreshToken();
    try { await A.api('/api/v1/auth/logout', { method: 'POST', body: rf ? { refresh_token: rf } : null }); } catch (e) {}
    A.clearTokens();
    dropUser();
    location.reload();
  }

  function changePassword(oldPassword, newPassword) {
    return A.api('/api/v1/auth/change-password', {
      method: 'POST', body: { old_password: oldPassword, new_password: newPassword }
    });
  }

  async function tryResume() {
    if (!A.getToken() && !A.getRefreshToken()) return false;
    var r = await A.api('/api/v1/auth/me');
    if (!r.ok) { A.clearTokens(); dropUser(); return false; }
    var payload = buildPayload(r.data);
    storeUser(payload);
    if (window.onKalLogin) window.onKalLogin(payload);
    return true;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var html = document.documentElement;
    try { if (localStorage.getItem('kal_theme') === 'dark') html.classList.add('dark'); } catch (e) {}
    document.addEventListener('click', function (ev) {
      if (ev.target.closest('#theme')) {
        var dark = html.classList.toggle('dark');
        try { localStorage.setItem('kal_theme', dark ? 'dark' : 'light'); } catch (e) {}
        return;
      }
      var exp = ev.target.closest('a[href*="/export/"], button[data-export]');
      if (exp) {
        var href = exp.getAttribute('href') || exp.getAttribute('data-export');
        if (href && href.indexOf('/export/') >= 0) {
          ev.preventDefault();
          A.downloadBlob(href, href.split('/').pop().split('?')[0] || 'export.csv');
        }
      }
    });

    var dlg = el('self-password-dialog'), openBtn = el('change-pass-btn'), form = el('self-password-form');
    if (dlg && openBtn && form) {
      openBtn.addEventListener('click', function () { dlg.showModal(); });
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var r = await changePassword(el('self-old-pass').value, el('self-new-pass').value);
        if (r.ok) { A.toast('Password changed successfully.'); form.reset(); dlg.close(); }
        else A.toast('Password change failed: ' + (r.detail || r.status), true);
      });
      dlg.addEventListener('click', function (ev) {
        if (ev.target.hasAttribute('data-cancel-self-pass') || ev.target === dlg) dlg.close();
      });
    }
  });

  window.KalAuth = {
    init: function () {
      formEl = el('login-form'); msgEl = el('login-msg'); btnEl = el('login-btn');
      A.state.onAuthLost = function () {
        A.clearTokens();
        var had = false;
        try { had = !!sessionStorage.getItem('kal_user'); } catch (e) {}
        dropUser();
        if (had) location.reload();
      };
      if (formEl) {
        formEl.addEventListener('submit', function (ev) {
          ev.preventDefault();
          var un = el('email').value.trim().toLowerCase(), pw = el('password').value;
          if (un && pw) login(un, pw);
        });
      }
      tryResume();
    },
    login: login, logout: logout, changePassword: changePassword, tryResume: tryResume
  };
})();
