(function(){
  'use strict';
  function apiBase(){
    var b = document.body.getAttribute('data-base') || '/';
    return b.replace(/\/+$/, '');
  }
  var root = document.getElementById('live');
  if (!root) return;

  var BASE = apiBase();
  var refreshMs = parseInt(root.getAttribute('data-refresh-ms') || '5000', 10);

  function normName(s){
    return String(s || '').toLowerCase().replace(/^stage\s*\d+\s*[-—:.]?\s*/i, '').trim();
  }

  // Map stage name -> card element
  var cards = {};
  root.querySelectorAll('.stage-live-card').forEach(function(el){
    var name = el.getAttribute('data-stage-name');
    if (name) cards[normName(name)] = el;
  });

  var venueMap = null;
  var venueReady = false;

  function fetchVenues(){
    if (venueReady) return Promise.resolve();
    return fetch(BASE + '/api/v1/public/venues', { credentials: 'omit' })
      .then(function(r){ return r.json(); })
      .then(function(d){
        venueMap = {};
        (d.venues || []).forEach(function(v){
          venueMap[normName(v.name)] = v.id;
        });
        venueReady = true;
      })
      .catch(function(){ venueReady = true; venueMap = {}; });
  }

  function setState(el, state){
    el.setAttribute('data-state', state);
    var label = el.querySelector('.stage-state-label');
    if (label) label.textContent = state;
    var badge = el.querySelector('.stage-state');
    if (badge){
      badge.setAttribute('data-state', state);
      if (state === 'RUNNING' || state === 'ON-STAGE'){
        badge.classList.add('is-live');
      } else {
        badge.classList.remove('is-live');
      }
    }
  }

  function renderStatus(d){
    var byId = {};
    (d.venues || []).forEach(function(v){ byId[v.id] = v; });

    Object.keys(cards).forEach(function(name){
      var card = cards[name];
      if (!document.body.contains(card)) return;
      var venueId = venueMap && venueMap[name];
      var v = venueId ? byId[venueId] : null;

      var stateEl = card.querySelector('.stage-state');
      var nowEl = card.querySelector('.stage-now-item');
      var upcomingEl = card.querySelector('.stage-upcoming-items');
      var nowLabel = card.querySelector('.stage-now-label');
      var upcomingLabel = card.querySelector('.stage-upcoming-label');

      if (!v){
        if (stateEl) setState(stateEl, 'IDLE');
        if (nowLabel) nowLabel.textContent = 'Live data:';
        if (nowEl) nowEl.innerHTML = '<span class="text-muted">not configured</span>';
        if (upcomingLabel) upcomingLabel.textContent = '';
        if (upcomingEl) upcomingEl.textContent = '';
        return;
      }

      if (stateEl) setState(stateEl, v.state || 'IDLE');

      var now = v.now;
      if (nowEl){
        if (now){
          var parts = [];
          if (now.roll) parts.push('<strong>Chest #' + escapeHtml(now.roll) + '</strong>');
          parts.push(escapeHtml(now.event || '—'));
          nowEl.innerHTML = parts.join(' · ');
        } else {
          nowEl.innerHTML = '<span class="text-muted">idle</span>';
        }
      }
      if (nowLabel) nowLabel.textContent = 'On stage:';

      if (upcomingLabel) upcomingLabel.textContent = 'Up next:';
      if (upcomingEl){
        var ups = (v.upcoming || []).slice(0, 4);
        if (ups.length){
          upcomingEl.innerHTML = ups.map(function(u){
            return u.roll ? '<strong>#' + escapeHtml(u.roll) + '</strong>' : '—';
          }).join(' &middot; ');
        } else {
          upcomingEl.textContent = '—';
        }
      }
    });
  }

  function escapeHtml(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function fail(){
    Object.keys(cards).forEach(function(name){
      var card = cards[name];
      if (!document.body.contains(card)) return;
      var nowEl = card.querySelector('.stage-now-item');
      var nowLabel = card.querySelector('.stage-now-label');
      var upcomingLabel = card.querySelector('.stage-upcoming-label');
      var upcomingEl = card.querySelector('.stage-upcoming-items');
      if (nowLabel) nowLabel.textContent = 'Live status:';
      if (nowEl) nowEl.innerHTML = '<span class="text-muted">unavailable in preview</span>';
      if (upcomingLabel) upcomingLabel.textContent = '';
      if (upcomingEl) upcomingEl.textContent = '';
    });
  }

  function poll(){
    if (!document.body.contains(root)){ clearInterval(timer); timer = null; return; }
    fetch(BASE + '/api/v1/public/status', { credentials: 'omit' })
      .then(function(r){ return r.json(); })
      .then(renderStatus)
      .catch(fail);
  }

  var timer = null;
  fetchVenues().then(function(){
    poll();
    timer = setInterval(poll, refreshMs);
  });

  // SPA router cleanup hook
  var cleanupFn = function(){
    if (timer){ clearInterval(timer); timer = null; }
  };
  if (window.KalApp && typeof window.KalApp.onCleanup === 'function') {
    window.KalApp.onCleanup(cleanupFn);
  } else {
    window.__kalCleanup = cleanupFn;
  }
})();