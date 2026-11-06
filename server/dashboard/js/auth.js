(function(){
  'use strict';
  var A = window.KalAPI;
  var msgEl, formEl, totpRow, btnEl;

  function msg(text, cls){
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }

  function showTotpRow(){
    totpRow.classList.remove('hidden');
    document.getElementById('totp').focus();
  }

  async function login(username, password, totp){
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var r = await fetch('/api/v1/auth/login', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, password: password, totp: totp || null })
      });
      var v = await r.json();
      if (v.error === 'totp_setup_required'){
        msg('First-time TOTP setup required. Add to authenticator, then enter the 6-digit code.');
        await setupTotp(username, password, v.uri);
        showTotpRow();
        msg('TOTP enrolled. Sign in with your code now.', 'ok');
        return false;
      }
      if (!r.ok){
        if (v.error === 'totp_required'){ showTotpRow(); msg('Enter your 6-digit authenticator code.', ''); return false; }
        if (v.error === 'account_locked'){
          msg('Locked — retry in ' + (v.retry_after || '') + 's.', 'err');
          return false;
        }
        msg('Sign-in failed.', 'err');
        return false;
      }
      sessionStorage.setItem('kal_user', JSON.stringify({
        username: v.username, role: v.role, stages: v.stages
      }));
      msg('Welcome, ' + v.username + '.', 'ok');
      if (window.onKalLogin) window.onKalLogin(v);
      return true;
    } catch(e){
      msg('Network error: ' + e.message, 'err');
      return false;
    } finally {
      btnEl.disabled = false;
    }
  }

  async function setupTotp(username, password, uri){
    var box = document.getElementById('enroll-box');
    if (!box){
      box = document.createElement('div');
      box.id = 'enroll-box';
      box.style.cssText = 'margin-top:1rem;padding:.8rem;background:#1e2532;border-radius:8px;font-family:ui-monospace,monospace;font-size:.78rem;word-break:break-all;white-space:pre-wrap';
      document.querySelector('.login-card').appendChild(box);
    }
    box.textContent = 'Add this account to your authenticator:\n\n' + uri;
    var code = prompt('Enter the 6-digit code from your authenticator:');
    box.remove();
    if (!code || !/^\d{6}$/.test(code)){ msg('Setup cancelled.', 'err'); return; }
    var c = await A.api('/api/v1/auth/totp/setup', {
      method: 'POST', body: { username: username, password: password, code: code }
    });
    if (!c.ok) msg('Setup failed: ' + (c.detail || 'bad_code'), 'err');
  }

  async function logout(){
    try { await A.api('/api/v1/auth/logout', { method: 'POST' }); } catch(e){}
    sessionStorage.removeItem('kal_user');
    location.reload();
  }

  async function tryResume(){
    var u = sessionStorage.getItem('kal_user');
    if (!u) return false;
    var r = await A.api('/api/v1/auth/me');
    if (r.ok && window.onKalLogin){ window.onKalLogin(JSON.parse(u)); return true; }
    sessionStorage.removeItem('kal_user');
    return false;
  }

  window.KalAuth = {
    init: function(){
      formEl = document.getElementById('login-form');
      msgEl = document.getElementById('login-msg');
      totpRow = document.getElementById('totp-row');
      btnEl = document.getElementById('login-btn');
      A.state.onAuthLost = function(){
        if (sessionStorage.getItem('kal_user')){
          sessionStorage.removeItem('kal_user');
          location.reload();
        }
      };
      formEl.addEventListener('submit', function(ev){
        ev.preventDefault();
        var un = document.getElementById('username').value.trim().toLowerCase();
        var pw = document.getElementById('password').value;
        var t = document.getElementById('totp').value.trim();
        if (un && pw) login(un, pw, t || null);
      });
      tryResume();
    },
    login: login,
    logout: logout
  };
})();
