(function(){
  'use strict';
  var K = window.Kal, root = document.getElementById('live');
  if (!K || !root) return;
  var BASE = K.apiBase();
  var _raw = parseInt(root.getAttribute('data-refresh-ms') || '10000', 10);
  var refreshMs = Math.max(5000, Number.isFinite(_raw) ? _raw : 10000);
  var cards = Array.from(root.querySelectorAll('.stage-live-card')).map(function(el){
    return { el: el, slug: el.getAttribute('data-stage-slug') || '', name: el.getAttribute('data-stage-name') || '' };
  });

  function setState(el, state){
    el.setAttribute('data-state', state);
    var label = el.querySelector('.stage-state-label');
    if (label) label.textContent = state;
    el.classList.toggle('is-live', state === 'RUNNING' || state === 'ON-STAGE');
  }

  function renderStatus(d){
    var venues = (d && d.venues) || [];
    cards.forEach(function(item){
      var card = item.el, v = venues.find(function(x){ return K.matchStage(x, item.slug, item.name); });
      var stateEl = card.querySelector('.stage-state'), nowEl = card.querySelector('.stage-now-item'),
          upEl = card.querySelector('.stage-upcoming-items'), nowLbl = card.querySelector('.stage-now-label'), upLbl = card.querySelector('.stage-upcoming-label');
      if (!v){
        if (stateEl) setState(stateEl, 'IDLE');
        if (nowLbl) nowLbl.textContent = 'Live data:';
        if (nowEl) nowEl.innerHTML = '<span class="text-muted">not configured</span>';
        if (upLbl) upLbl.textContent = ''; if (upEl) upEl.textContent = '';
        return;
      }
      if (stateEl) setState(stateEl, v.state || 'IDLE');
      if (v.active === false || v.state === 'INACTIVE'){
        if (nowLbl) nowLbl.textContent = 'Status:';
        if (nowEl) nowEl.innerHTML = '<span class="text-muted">Stage inactive</span>';
        if (upLbl) upLbl.textContent = ''; if (upEl) upEl.textContent = '';
        return;
      }
      if (nowLbl) nowLbl.textContent = 'On stage:';
      if (upLbl) upLbl.textContent = 'Up next:';
      if (nowEl){
        if (v.now){
          var parts = [];
          if (v.now.roll) parts.push('<strong>Chest #' + K.esc(v.now.roll) + '</strong>');
          if (v.now.event) parts.push(K.esc(v.now.event));
          nowEl.innerHTML = parts.length ? parts.join(' · ') : '<span class="text-muted">on stage</span>';
        } else nowEl.innerHTML = '<span class="text-muted">idle</span>';
      }
      if (upEl){
        var ups = (v.upcoming || []).slice(0, 4);
        upEl.innerHTML = ups.length ? ups.map(function(u){ return u.roll ? '<strong>#' + K.esc(u.roll) + '</strong>' : '—'; }).join(' &middot; ') : '—';
      }
    });
  }

  function fail(){
    cards.forEach(function(item){
      var c = item.el, nl = c.querySelector('.stage-now-label'), ne = c.querySelector('.stage-now-item'),
          ul = c.querySelector('.stage-upcoming-label'), ue = c.querySelector('.stage-upcoming-items');
      if (nl) nl.textContent = 'Live status:';
      if (ne) ne.innerHTML = '<span class="text-muted">unavailable</span>';
      if (ul) ul.textContent = ''; if (ue) ue.textContent = '';
    });
  }

  K.poll(function(){
    fetch(BASE + '/api/v1/public/status', { credentials: 'omit' })
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(renderStatus).catch(fail);
  }, refreshMs);
})();
