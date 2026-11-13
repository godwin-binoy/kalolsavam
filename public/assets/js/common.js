(function(){
  'use strict';

  function apiBase(){
    if (typeof window.KAL_API_BASE === 'string' && window.KAL_API_BASE) {
      return window.KAL_API_BASE.replace(/\/+$/, '');
    }
    var explicit = document.body && document.body.getAttribute('data-api');
    if (explicit === 'same-origin' || explicit === '') return '';
    if (explicit != null) return explicit.replace(/\/+$/, '');
    if (location.port === '8000' || location.hostname === 'testserver') return '';
    return 'https://apikalolsavammala.dpdns.org';
  }

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function normName(s){
    return String(s || '').toLowerCase().replace(/^stage\s*\d+\s*[-—:.]?\s*/i, '').trim();
  }

  function matchStage(venue, wantSlug, wantName){
    if (!venue) return false;
    if (wantSlug && venue.slug && String(venue.slug).toLowerCase() === String(wantSlug).toLowerCase()) {
      return true;
    }
    return normName(venue.name) === normName(wantName);
  }

  function poll(fn, intervalMs){
    var timer = null;
    var stopped = false;

    function tick(){
      if (!stopped && !document.hidden) fn();
    }
    function start(){
      if (stopped || timer) return;
      timer = setInterval(tick, intervalMs);
    }
    function stop(){
      if (timer){ clearInterval(timer); timer = null; }
    }
    function onVis(){
      if (document.hidden) stop();
      else { tick(); start(); }
    }

    fn();
    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVis);

    return function(){
      stopped = true;
      stop();
      document.removeEventListener('visibilitychange', onVis);
    };
  }

  window.Kal = {
    apiBase: apiBase,
    esc: esc,
    normName: normName,
    matchStage: matchStage,
    poll: poll
  };
})();
