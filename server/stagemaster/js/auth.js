/* Shared login/session logic for both dashboards (stagemaster + admin).
 * Implements the SRP-6a flow against /api/auth, plus TOTP prompt and the
 * first-run TOTP enrollment wizard. Session token lives in memory only. */
(function () {
  'use strict';

  var K = window.KalSRP, A = window.KalAPI;
  var msgEl, formEl, totpRow, btnEl;

  function msg(text, cls) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }

  /* ---- full SRP login: challenge -> verify (+ optional TOTP) ---- */
  async function login(username, password, totp) {
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var st = await K.clientStart(username, password);
      var r1 = await fetch('/api/auth/challenge', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, A: st.A_hex })
      });
      var c = await r1.json();
      if (!r1.ok) {
        var d = c.detail || {};
        if (d.retry_after) msg('Too many attempts — locked for ' + d.retry_after + 's.', 'err');
        else msg('Sign-in failed.', 'err');
        return false;
      }
      var fin = await K.clientFinish(st, c.salt, c.B);
      var r2 = await fetch('/api/auth/verify', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sid: c.sid, M1: fin.M1_hex, totp: totp || null })
      });
      var v = await r2.json();
      if (r2.status === 401 && v.detail && v.detail.detail === 'totp_enrollment_required') {
        // SRP passed but no authenticator yet → run enrollment wizard
        A.setTokens(v.detail.access, v.detail.csrf);
        await enrollTotp();
        return login(username, password, null);   // now sign in normally
      }
      if (r2.status === 401 && v.detail === 'totp_required') {
        showTotpRow('Enter the 6-digit code from your authenticator app.');
        return false;
      }
      if (!r2.ok) { msg('Sign-in failed (bad credentials or expired challenge).', 'err'); return false; }
      // mutual auth: verify the server's M2 matches our computed session key
      if (v.M2 && v.M2.toLowerCase() !== fin.M2_expected_hex) {
        msg('Server proof mismatch — possible impostor. Aborting.', 'err');
        A.clear();
        return false;
      }
      A.setTokens(v.access, v.csrf);
      sessionStorage.setItem('kal_user', JSON.stringify(
        { username: v.username, role: v.role, stages: v.stages }));
      msg('Welcome, ' + v.username + '.', 'ok');
      if (window.onKalLogin) window.onKalLogin(v);
      return true;
    } catch (e) {
      msg('Network error: ' + e.message, 'err');
      return false;
    } finally {
      btnEl.disabled = false;
    }
  }

  /* ---- first-run TOTP enrollment wizard ---- */
  function showEnrollInfo(uri) {
    // Dependency-free + CSP-safe: display the base32 secret so it can be
    // typed/scanned into any authenticator app, plus the full otpauth URI.
    var m = uri.match(/[?&]secret=([A-Z2-7]+)/i);
    var lines = [
      'TOTP setup — add this account to your authenticator app:',
      '',
      'Secret (base32): ' + (m ? m[1].replace(/(.{4})/g, '$1 ').trim() : '(see URI)'),
      '',
      'Or paste the full URI manually:',
      uri
    ];
    var box = document.getElementById('enroll-box');
    if (!box) {
      box = document.createElement('div');
      box.id = 'enroll-box';
      box.className = 'panel';
      box.style.cssText = 'margin-top:1rem;text-align:left;white-space:pre-wrap;' +
        'word-break:break-all;font-family:ui-monospace,monospace;font-size:.85rem';
      document.querySelector('.login-card').appendChild(box);
    }
    box.textContent = lines.join('\n');
  }

  async function enrollTotp() {
    msg('Setting up your authenticator app…');
    var r = await A.api('/api/auth/totp/start', { method: 'POST' });
    if (!r.ok) { msg('Could not start TOTP setup.', 'err'); return; }
    var uri = r.data.uri, token = r.data.confirm_token;
    showEnrollInfo(uri);
    var code = prompt('Enter the current 6-digit code from your app\n(cancel to abort enrollment):');
    var box = document.getElementById('enroll-box');
    if (box) box.remove();
    if (!code || !/^\d{6}$/.test(code)) { msg('Enrollment cancelled — sign in again after enrolling.', 'err'); return; }
    var c = await A.api('/api/auth/totp/confirm', {
      method: 'POST', body: { confirm_token: token, code: code }
    });
    if (c.ok) msg('Authenticator enrolled. You can sign in now.', 'ok');
    else msg('Enrollment failed: ' + (c.detail || 'bad code'), 'err');
  }

  function showTotpRow(text) {
    totpRow.classList.remove('hidden');
    totpRow.querySelector('label').firstChild.textContent = text + ' ';
    document.getElementById('totp').focus();
  }

  async function logout() {
    try { await A.api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
    A.clear();
    sessionStorage.removeItem('kal_user');
    location.reload();
  }

  /* restore a live page (e.g. refresh with valid refresh cookie) */
  async function tryResume() {
    if (await A.refresh()) {
      var u = sessionStorage.getItem('kal_user');
      if (u && window.onKalLogin) {
        window.onKalLogin(JSON.parse(u));
        return true;
      }
    }
    return false;
  }

  window.KalAuth = {
    init: function (opts) {
      formEl = document.getElementById('login-form');
      msgEl = document.getElementById('login-msg');
      totpRow = document.getElementById('totp-row');
      btnEl = document.getElementById('login-btn');
      A.state.onAuthLost = function () { location.reload(); };
      formEl.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var un = document.getElementById('username').value.trim().toLowerCase();
        var pw = document.getElementById('password').value;
        var t  = document.getElementById('totp').value.trim();
        if (un && pw) login(un, pw, t || null);
      });
      if (opts && opts.resume !== false) tryResume();
    },
    login: login,
    logout: logout,
    tryResume: tryResume
  };
})();
