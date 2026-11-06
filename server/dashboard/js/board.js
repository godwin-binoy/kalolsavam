(function(){
  'use strict';
  var A = window.KalAPI;
  var boardsEl, connEl, whoEl;
  var feed = null;
  var lastAction = {};

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  async function loadBoard(){
    var r = await A.api('/api/v1/live/board');
    if (!r.ok){
      if (r.status === 401 || r.status === 403){ location.reload(); return; }
      A.toast('Could not load board: ' + (r.detail || r.status), true);
      return;
    }
    render(r.data.board || []);
  }

  function render(board){
    boardsEl.innerHTML = '';
    if (!board.length){
      boardsEl.innerHTML = '<div class="panel"><p class="muted">No stages are assigned to your account.</p></div>';
      return;
    }
    board.forEach(function(v){ boardsEl.appendChild(venuePanel(v)); });
  }

  function venuePanel(v){
    var venue = v.venue, state = v.state || { state: 'IDLE' }, items = v.items || [];
    var p = document.createElement('section');
    p.className = 'panel';
    p.dataset.venue = venue.id;

    var cur = items.filter(function(i){ return i.status === 'ON-STAGE'; })[0];
    var next = items.filter(function(i){ return i.status === 'WAITING'; })[0];
    var rows = items.map(function(i){
      var tr = document.createElement('tr');
      if (i.status === 'ON-STAGE') tr.className = 'onstage';
      tr.innerHTML =
        '<td>' + (i.position + 1) + '</td>' +
        '<td>' + esc(i.event || '') + '<br><span class="muted small">' + esc(i.category || '') + '</span></td>' +
        '<td>' + esc(i.school || '—') + '<br><span class="muted small">' + esc(i.student_name || '') + '</span></td>' +
        '<td><span class="status ' + esc(i.status) + '">' + esc(i.status) + '</span></td>' +
        '<td>' + (['ON-STAGE','PAUSED','COMPLETE'].indexOf(i.status) >= 0
          ? '<button data-act="score" data-id="' + i.id + '">Score</button>' : '') + '</td>';
      return tr;
    }).join('');

    p.innerHTML =
      '<div class="row"><h2>' + esc(venue.name) + '</h2>' +
        '<span class="state-pill state-' + esc(state.state) + '">' + esc(state.state) + '</span>' +
        '<span class="spacer" style="flex:1"></span></div>' +
      (state.announcement ? '<p class="small muted">📣 ' + esc(state.announcement) + '</p>' : '') +
      '<div class="row" style="margin:.6rem 0">' +
        '<button data-act="START_NEXT" class="primary">▶ Start next' +
          (next ? ' (' + esc(next.student_name || next.event || '') + ')' : '') + '</button>' +
        '<button data-act="COMPLETE_CURRENT"' + (cur ? '' : ' disabled') + '>✔ Complete</button>' +
        '<button data-act="PAUSE"' + (cur ? '' : ' disabled') + '>⏸ Pause</button>' +
        '<button data-act="RESUME"' + (cur && cur.status === 'PAUSED' ? '' : ' disabled') + '>⏵ Resume</button>' +
        '<button data-act="SKIP"' + (next ? '' : ' disabled') + '>⏭ Skip next</button>' +
      '</div>' +
      '<div class="row" style="margin-bottom:.6rem">' +
        '<select id="vstate-' + venue.id + '">' +
          ['IDLE','RUNNING','PAUSED','BREAK','FINISHED'].map(function(s){
            return '<option' + (s === state.state ? ' selected' : '') + '>' + s + '</option>';
          }).join('') +
        '</select>' +
        '<input id="vann-' + venue.id + '" placeholder="Announcement" maxlength="280" value="' +
          esc(state.announcement || '') + '" style="flex:1">' +
        '<button data-act="pushstate">Post</button>' +
      '</div>' +
      '<table><thead><tr><th>#</th><th>Event</th><th>Performer</th><th>Status</th><th></th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table>';

    p.addEventListener('click', function(ev){
      var b = ev.target.closest('button[data-act]');
      if (!b || b.disabled) return;
      var act = b.dataset.act;
      if (act === 'score'){ openScoreDialog(b.dataset.id); return; }
      if (act === 'pushstate'){
        var sel = p.querySelector('#vstate-' + venue.id);
        var ann = p.querySelector('#vann-' + venue.id);
        postState(venue.id, sel.value, ann.value);
        return;
      }
      advance(venue.id, act);
    });
    return p;
  }

  function idemKey(){
    return 'sm-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  }

  async function advance(venueId, action){
    lastAction[venueId] = Date.now();
    var r = await A.api('/api/v1/live/advance', {
      method: 'POST',
      headers: { 'Idempotency-Key': idemKey() },
      body: { venue_id: Number(venueId), action: action }
    });
    if (!r.ok){
      if (r.detail === 'version_conflict' || r.detail === 'no_item_in_state'){
        A.toast('Board changed — re-syncing.'); loadBoard();
      } else A.toast('Action failed: ' + (r.detail || r.status), true);
      return;
    }
    loadBoard();
  }

  async function postState(venueId, state, announcement){
    var r = await A.api('/api/v1/live/state', {
      method: 'POST',
      body: { venue_id: Number(venueId), state: state, announcement: announcement || '' }
    });
    if (!r.ok) A.toast('Status update failed', true);
    else { A.toast('Posted.'); loadBoard(); }
  }

  var scoreTarget = null;
  function openScoreDialog(itemId){
    scoreTarget = Number(itemId);
    var dlg = document.getElementById('score-dialog');
    var sel = document.getElementById('score-judge');
    sel.innerHTML = '';
    for (var j = 1; j <= 5; j++){
      var o = document.createElement('option');
      o.value = String(j); o.textContent = 'Judge ' + j;
      sel.appendChild(o);
    }
    document.getElementById('score-value').value = '';
    document.getElementById('score-who').textContent = 'Queue item #' + itemId;
    dlg.showModal();
  }

  document.addEventListener('DOMContentLoaded', function(){
    var form = document.getElementById('score-form');
    form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var submitter = ev.submitter;
      document.getElementById('score-dialog').close();
      if (!submitter || submitter.value !== 'save') return;
      if (!scoreTarget) return;
      var r = await A.api('/api/v1/live/score', {
        method: 'POST',
        body: {
          queue_item_id: scoreTarget,
          judge_no: Number(document.getElementById('score-judge').value),
          value: Number(document.getElementById('score-value').value)
        }
      });
      if (!r.ok) A.toast('Score rejected', true);
      else A.toast('Saved — total ' + r.data.total);
    });
  });

  function startFeed(){
    if (feed) feed.close();
    feed = A.stream('/api/v1/live/stream', {
      onopen: function(){ connEl.textContent = 'live'; connEl.className = 'badge live'; },
      onmissed: function(){ connEl.textContent = 'reconnecting…'; connEl.className = 'badge offline'; },
      '*': function(msg){
        var vid = msg.venue_id;
        if (vid && lastAction[vid] && Date.now() - lastAction[vid] < 1200) return;
        loadBoard();
      }
    });
  }

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    whoEl.textContent = info.username + ' · ' + info.role;
    loadBoard();
    startFeed();
  };

  document.addEventListener('DOMContentLoaded', function(){
    boardsEl = document.getElementById('boards');
    connEl = document.getElementById('conn');
    whoEl = document.getElementById('who');
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('sync-btn').addEventListener('click', loadBoard);
    window.KalAuth.init();
  });
})();
