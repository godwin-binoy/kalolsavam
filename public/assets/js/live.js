(function(){
  'use strict';
  var K = window.Kal;
  var root = document.getElementById('live');
  if (!K || !root) return;

  var BASE = K.apiBase();
  var _raw = parseInt(root.getAttribute('data-refresh-ms') || '10000', 10);
  if (!Number.isFinite(_raw)) _raw = 10000;
  var refreshMs = Math.max(5000, _raw);

  var cardList = [];
  root.querySelectorAll('.stage-live-card').forEach(function(el){
    cardList.push({
      el: el,
      slug: el.getAttribute('data-stage-slug') || '',
      name: el.getAttribute('data-stage-name') || ''
    });
  });

  function setState(el, state){
    el.setAttribute('data-state', state);
    var label = el.querySelector('.stage-state-label');
    if (label) label.textContent = state;
    if (state === 'RUNNING' || state === 'ON-STAGE') el.classList.add('is-live');
    else el.classList.remove('is-live');
  }

  function renderStatus(d){
    var venues = (d && d.venues) || [];
    cardList.forEach(function(item){
      var card = item.el;
      var v = null;
      for (var i = 0; i < venues.length; i++){
        if (K.matchStage(venues[i], item.slug, item.name)){ v = venues[i]; break; }
      }

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
          if (now.roll) parts.push('<strong>Chest #' + K.esc(now.roll) + '</strong>');
          parts.push(K.esc(now.event || '—'));
          nowEl.innerHTML = parts.join(' · ');
        } else {
          nowEl.innerHTML = '<span class="text-muted">idle</span>';
        }
      }
      if (nowLabel) nowLabel.textContent = 'On stage:';
      if (upcomingLabel) upcomingLabel.textContent = 'Up next:';
      if (upcomingEl){
        var ups = (v.upcoming || []).slice(0, 4);
        upcomingEl.innerHTML = ups.length
          ? ups.map(function(u){ return u.roll ? '<strong>#' + K.esc(u.roll) + '</strong>' : '—'; }).join(' &middot; ')
          : '—';
      }
    });
  }

  function fail(){
    cardList.forEach(function(item){
      var card = item.el;
      var nowEl = card.querySelector('.stage-now-item');
      var nowLabel = card.querySelector('.stage-now-label');
      var upcomingLabel = card.querySelector('.stage-upcoming-label');
      var upcomingEl = card.querySelector('.stage-upcoming-items');
      if (nowLabel) nowLabel.textContent = 'Live status:';
      if (nowEl) nowEl.innerHTML = '<span class="text-muted">unavailable</span>';
      if (upcomingLabel) upcomingLabel.textContent = '';
      if (upcomingEl) upcomingEl.textContent = '';
    });
  }

  K.poll(function(){
    fetch(BASE + '/api/v1/public/status', { credentials: 'omit' })
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(renderStatus)
      .catch(fail);
  }, refreshMs);
})();
