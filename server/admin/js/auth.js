/* Shared login/session logic for both dashboards (stagemaster + admin).
 * Simple flow: POST /api/auth/login with username+password(+TOTP). HTTPS at
 * Cloudflare's edge protects the wire; rate limits, lockouts and TOTP protect
 * the accounts. The access token lives in memory only — never localStorage. */
(function () {
  'use strict';

  var A = window.KalAPI;
  var msgEl, formEl, totpRow, btnEl;

  function msg(text, cls) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }

  /* ---- one-step login (+ optional first-run TOTP enrollment) ---- */
  async function login(username, password, totp) {
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var r = await fetch('/api/auth/login', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, password: password,
                               totp: totp || null })
      });
      var v = await r.json();
      var d = (v && typeof v.detail === 'object' && v.detail) ? v.detail
              : { detail: v && v.detail };
      if (r.status === 429 && d.retry_after) {
        msg('Too many attempts — locked for ' + d.retry_after + 's.', 'err');
        return false;
      }
      if (r.status === 401 && d.detail === 'totp_enrollment_required') {
        // Password OK but no authenticator yet → run enrollment wizard,
        // then sign in again normally.
        A.setTokens(d.access, d.csrf);
        await enrollTotp();
        return login(username, password, null);
      }
      if (r.status === 401 && d.detail === 'totp_required') {
        showTotpRow('Enter the 6-digit code from your authenticator app.');
        return false;
      }
      if (!r.ok || !v.access) { msg('Sign-in failed.', 'err'); return false; }
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
