/* Staff sign-in / session resume. Session resume now uses the refresh path. */
(function () {
  'use strict';

  var A = window.KalAPI;
  var msgEl, formEl, btnEl;

  function msg(text, cls) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }

  function storeUser(payload) {
    try { sessionStorage.setItem('kal_user', JSON.stringify(payload)); } catch (e) {}
  }
  function dropUser() {
    try { sessionStorage.removeItem('kal_user'); } catch (e) {}
  }

  function buildPayload(info) {
    info = info || {};
    var roles = Array.isArray(info.roles) ? info.roles : [];
    var first = roles[0];
    var role = (first && (first.name || first)) || info.role || '';
    var name = info.email || info.username || '';
    return {
      username: name,
      email: name,
      role: role,
      roles: roles,
      stages: info.stages || []
    };
  }

  async function login(username, password) {
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var r = await fetch(A.url('/api/v1/auth/login'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: username, password: password })
      });
      var v = await r.json().catch(function () { return {}; });
      if (!r.ok) {
        var why = (v && (v.error || v.detail)) || ('Sign-in failed (' + r.status + ').');
        msg(typeof why === 'string' ? why : 'Sign-in failed.', 'err');
        return false;
      }
      if (v && v.access_token) A.setToken(v.access_token);
      if (v && v.refresh_token) A.setRefreshToken(v.refresh_token);

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
    try { await A.api('/api/v1/auth/logout', { method: 'POST' }); } catch (e) {}
    A.clearTokens();
    dropUser();
    location.reload();
  }

  async function changePassword(oldPassword, newPassword) {
    return await A.api('/api/v1/auth/change-password', {
      method: 'POST',
      body: { old_password: oldPassword, new_password: newPassword }
    });
  }

  async function tryResume() {
    if (!A.getToken() && !A.getRefreshToken()) return false;
    var r = await A.api('/api/v1/auth/me');
    if (!r.ok) {
      A.clearTokens();
      dropUser();
      return false;
    }
    var payload = buildPayload(r.data);
    storeUser(payload);
    if (window.onKalLogin) window.onKalLogin(payload);
    return true;
  }

  window.KalAuth = {
    init: function () {
      formEl = document.getElementById('login-form');
      msgEl = document.getElementById('login-msg');
      btnEl = document.getElementById('login-btn');

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
          var un = document.getElementById('email').value.trim().toLowerCase();
          var pw = document.getElementById('password').value;
          if (un && pw) login(un, pw);
        });
      }
      tryResume();
    },
    login: login,
    logout: logout,
    changePassword: changePassword,
    tryResume: tryResume
  };
})();
