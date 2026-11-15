(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var boardsEl, connEl, whoEl;
  var feed = null;
  var boardData = [];
  var lastAction = {};

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
    boardData = board;
    boardsEl.innerHTML = '';
    
    // Populate photo intake
    var photoSec = document.getElementById('photo-intake');
    var sel = document.getElementById('photo-item-select');
    if (photoSec && sel) {
      photoSec.style.display = 'block';
      sel.innerHTML = '<option value="">-- Choose an item --</option>';
      board.forEach(function(v){
        var activeItems = v.items.filter(function(i){ return i.status === 'ON-STAGE' || i.status === 'PAUSED' || i.status === 'WAITING'; });
        activeItems.forEach(function(i){
          var o = document.createElement('option');
          o.value = i.id;
          o.textContent = v.venue.name + ' - ' + (i.chest_no ? 'Chest '+i.chest_no+' - ' : '') + i.event;
          sel.appendChild(o);
        });
      });
    }
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

    var cur = items.filter(function(i){ return i.status === 'ON-STAGE' || i.status === 'PAUSED'; })[0];
    var next = items.filter(function(i){ return i.status === 'WAITING'; })[0];
    var rows = items.map(function(i){
      var rowClass = i.status === 'ON-STAGE' ? ' class="onstage"' : '';
      var actions = '';
      if (i.status === 'COMPLETE'){
        actions += ' <button data-act="recall" data-id="' + esc(i.id) + '" data-ver="' + esc(i.version) + '">Recall</button>';
      }
      return '<tr' + rowClass + ' data-status="' + esc(i.status) + '" data-ver="' + esc(i.version) + '">' +
        '<td>' + (i.chest_no ? '<strong>' + esc(i.chest_no) + '</strong>' : '—') + '</td>' +
        '<td>' + esc(i.event || '') + '<br><span class="muted small">' + esc(i.category || '') + '</span></td>' +
        '<td>' + esc(i.school || '—') + '<br><span class="muted small">' + esc(i.student_name || '') + '</span></td>' +
        '<td><span class="status ' + esc(i.status) + '">' + esc(i.status) + '</span></td>' +
        '<td>' + actions + '</td>' +
      '</tr>';
    }).join('');

    p.innerHTML =
      '<div class="row"><h2>' + esc(venue.name) + '</h2>' +
        '<span class="state-pill state-' + esc(state.state) + '">' + esc(state.state) + '</span>' +
        '<span class="spacer" style="flex:1"></span></div>' +
      (state.announcement ? '<p class="small muted">📣 ' + esc(state.announcement) + '</p>' : '') +
      '<div class="row" style="margin:.6rem 0">' +
        '<button data-act="START_NEXT" class="primary"' + (next ? '' : ' disabled') + '>▶ Start next' +
          (next ? ' (' + esc(next.student_name || next.event || '') + ')' : '') + '</button>' +
        '<button data-act="COMPLETE_CURRENT"' + (cur && cur.status === 'ON-STAGE' ? '' : ' disabled') + '>✔ Complete</button>' +
        '<button data-act="PAUSE"' + (cur && cur.status === 'ON-STAGE' ? '' : ' disabled') + '>⏸ Pause</button>' +
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
      '<table><thead><tr><th>Chest</th><th>Event</th><th>Performer</th><th>Status</th><th></th></tr></thead>' +
      '<tbody>' + (rows || '<tr><td colspan="5" class="muted">No items queued.</td></tr>') + '</tbody></table>';

    p.addEventListener('click', function(ev){
      var b = ev.target.closest('button[data-act]');
      if (!b || b.disabled) return;
      var act = b.dataset.act;
      if (act === 'recall'){ advance(venue.id, 'RECALL', Number(b.dataset.id), Number(b.dataset.ver)); return; }
      if (act === 'pushstate'){
        var sel = p.querySelector('#vstate-' + venue.id);
        var ann = p.querySelector('#vann-' + venue.id);
        postState(venue.id, sel.value, ann.value);
        return;
      }
      if (act === 'START_NEXT') {
        var next = items.filter(function(i){ return i.status === 'WAITING'; })[0];
        var defaultChest = (next && next.roll) ? next.roll : '';
        var chest = prompt("Enter chest number for the starting item:", defaultChest);
        if (chest === null) return; // Cancelled
        advance(venue.id, act, null, null, chest.trim() || null);
        return;
      }
      advance(venue.id, act);
    });
    return p;
  }

  function idemKey(){
    return 'sm-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  }

  var FROM_STATUS = {
    START_NEXT: 'WAITING', COMPLETE_CURRENT: 'ON-STAGE', PAUSE: 'ON-STAGE',
    RESUME: 'PAUSED', SKIP: 'WAITING', RECALL: 'COMPLETE'
  };

  async function advance(venueId, action, itemId, itemVersion, chestNo){
    lastAction[venueId] = Date.now();

    var panel = document.querySelector('.panel[data-venue="' + venueId + '"]');
    var prevStates = [];
    if (panel) {
      panel.querySelectorAll('button').forEach(function(b){
        prevStates.push([b, b.disabled]);
        b.disabled = true;
      });
    }

    var version = (typeof itemVersion === 'number') ? itemVersion : null;
    if (version == null) {
      var fromStatus = FROM_STATUS[action];
      if (panel && fromStatus) {
        var tr = panel.querySelector('tr[data-status="' + fromStatus + '"]');
        if (tr && tr.dataset.ver) version = Number(tr.dataset.ver);
      }
    }

    var payload = { venue_id: Number(venueId), action: action, version: version };
    if (chestNo) payload.chest_no = chestNo;
    if (typeof itemId === 'number') payload.item_id = itemId;

    try {
      var r = await A.api('/api/v1/live/advance', {
        method: 'POST',
        headers: { 'Idempotency-Key': idemKey() },
        body: payload
      });
      if (!r.ok){
        if (r.detail === 'version_conflict' || r.detail === 'no_item_in_state'
            || r.detail === 'state_changed'){
          A.toast('Board changed — re-syncing.'); await loadBoard();
        } else {
          A.toast('Action failed: ' + (r.detail || r.status), true);
        }
        return;
      }
      await loadBoard();
    } finally {
      if (panel && document.body.contains(panel)){
        prevStates.forEach(function(pair){ pair[0].disabled = pair[1]; });
      }
    }
  }

  async function postState(venueId, state, announcement){
    var r = await A.api('/api/v1/live/state', {
      method: 'POST',
      body: { venue_id: Number(venueId), state: state, announcement: announcement || '' }
    });
    if (!r.ok) A.toast('Status update failed', true);
    else { A.toast('Posted.'); loadBoard(); }
  }

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
    whoEl.textContent = (info.username || info.email || 'staff') + ' · ' + (info.role || 'stagemaster');
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

  // ---- Photo Intake Logic ----
  window.uploadPhotos = async function(workflow) {
    var sel = document.getElementById('photo-item-select');
    var itemId = Number(sel.value);
    if (!itemId) { A.toast('Select an item first', true); return; }
    
    var currentVenue = null;
    var currentItem = null;
    for (var i=0; i<boardData.length; i++) {
       var it = boardData[i].items.find(x => x.id === itemId);
       if (it) { currentVenue = boardData[i].venue; currentItem = it; break; }
    }
    if (!currentVenue) return;
    
    var batchReq = await A.api('/api/v1/photos/batches', {
      method: 'POST',
      body: { queue_item_id: itemId, venue_id: currentVenue.id, perf_date: new Date().toISOString().split('T')[0], workflow: workflow }
    });
    if (!batchReq.ok) { A.toast('Batch creation failed', true); return; }
    var batchId = batchReq.data.batch_id;
    
    var files = [];
    if (workflow === 'bulk') {
      var slips = document.getElementById('w1-slips').files;
      for (var i=0; i<slips.length; i++) files.push({kind: 'slip', file: slips[i]});
      var stages = document.getElementById('w1-stage').files;
      for (var i=0; i<stages.length; i++) files.push({kind: 'stage', file: stages[i]});
    } else {
      var stages = document.getElementById('w2-stage').files;
      for (var i=0; i<stages.length; i++) files.push({kind: 'stage', file: stages[i]});
    }
    
    A.toast('Uploading ' + files.length + ' photos...');
    
    for (var i=0; i<files.length; i++) {
      var fd = new FormData();
      fd.append('kind', files[i].kind);
      fd.append('file', files[i].file);
      
      var res = await fetch(A.url('/api/v1/photos/batches/'+batchId+'/upload'), {
        method: 'POST', headers: {'Authorization': 'Bearer ' + A.getToken()}, body: fd
      });
      var data = await res.json();
      
      // Auto-assign for workflow 2
      if (workflow === 'quick' && currentItem.participant_entry_id) {
        await A.api('/api/v1/photos/assign', {
          method: 'POST',
          body: { asset_id: data.asset_id, participant_entry_ids: [currentItem.participant_entry_id] }
        });
      }
    }
    
    if (workflow === 'quick') {
      await A.api('/api/v1/photos/batches/'+batchId+'/publish', { method: 'POST' });
    }
    
    A.toast('Upload complete');
  };
