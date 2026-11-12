(function(){
  'use strict';
  var A = window.KalAPI;
  var msgEl, formEl, btnEl;

  function msg(text, cls){
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'msg' + (cls ? ' ' + cls : '');
  }

  async function login(username, password){
    btnEl.disabled = true;
    msg('Signing in…');
    try {
      var r = await fetch('/api/v1/auth/login', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: username, password: password })
      });
      var v = await r.json().catch(function(){ return {}; });
      if (!r.ok){
        // Backend emits {"error": "..."} (see server/errors.py) and Pydantic
        // emits {"detail": ...}. Prefer either, fall back to the status code.
        var why = (v && (v.error || v.detail)) || ('Sign-in failed (' + r.status + ').');
        msg(typeof why === 'string' ? why : 'Sign-in failed.', 'err');
        return false;
      }
      var me = await A.api('/api/v1/auth/me');
      var info = me.ok ? me.data : v;
      var _roles = info.roles || [];
      var _role = (Array.isArray(_roles) && _roles[0] && (_roles[0].name || _roles[0])) || info.role || '';
      var _name = info.email || info.username || '';
      var payload = {
        username: _name,
        email: _name,
        role: _role,
        roles: Array.isArray(_roles) ? _roles : [],
        stages: info.stages || []
      };
      sessionStorage.setItem('kal_user', JSON.stringify(payload));
      msg('Signed in as ' + (_name || 'user') + '.', 'ok');
      if (window.onKalLogin) window.onKalLogin(payload);
      return true;
    } catch(e){
      msg('Network error: ' + e.message, 'err');
      return false;
    } finally {
      btnEl.disabled = false;
    }
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
      btnEl = document.getElementById('login-btn');
      A.state.onAuthLost = function(){
        if (sessionStorage.getItem('kal_user')){
          sessionStorage.removeItem('kal_user');
          location.reload();
        }
      };
      formEl.addEventListener('submit', function(ev){
        ev.preventDefault();
        var un = document.getElementById('email').value.trim().toLowerCase();
        var pw = document.getElementById('password').value;
        if (un && pw) login(un, pw);
      });
      tryResume();
    },
    login: login,
    logout: logout
  };
})();
