(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var boardsEl, connEl, whoEl;
  var feed = null;
  var boardData = [];
  var scheduleEvents = [];
  var lastAction = {};

  // Photo intake state
  var photoFiles = { w1Slips: [], w1Stage: [], w2Stage: [] };
  var previewUrls = { w1Slips: [], w1Stage: [], w2Stage: [] };
  var w2SelectedRegs = []; // [{ register_no, label }]

  async function loadSchedule(){
    var r = await A.api('/api/v1/public/schedule');
    if (r.ok && r.data && Array.isArray(r.data.events)){
      scheduleEvents = r.data.events;
      populateW2Items();
    }
  }

  function populateW2Items(){
    var sel = document.getElementById('w2-item');
    var custom = document.getElementById('w2-item-custom');
    if (!sel) return;
    var prev = sel.value;
    var opts = '<option value="">-- Select item --</option>' +
      scheduleEvents.map(function(e){
        return '<option value="' + esc(e.code) + '">' + esc(e.code) + ' · ' + esc(e.title) + '</option>';
      }).join('') +
      '<option value="__custom__">Other / Enter item code…</option>';
    sel.innerHTML = opts;
    if (prev) sel.value = prev;
    if (!scheduleEvents.length){
      sel.value = '__custom__';
    }
    if (custom) custom.style.display = sel.value === '__custom__' ? 'block' : 'none';
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
    boardData = board;
    boardsEl.innerHTML = '';

    var photoSec = document.getElementById('photo-intake');
    var vSel = document.getElementById('photo-venue-select');
    if (photoSec && vSel){
      photoSec.style.display = board.length ? 'block' : 'none';
      var prevV = vSel.value;
      vSel.innerHTML = board.map(function(b){
        return '<option value="' + b.venue.id + '">' + esc(b.venue.name) + '</option>';
      }).join('');
      if (prevV && board.some(function(b){ return String(b.venue.id) === String(prevV); })){
        vSel.value = prevV;
      }
    }

    if (!board.length){
      boardsEl.innerHTML = '<div class="panel"><p class="muted">No stages are assigned to your account.</p></div>';
      return;
    }
    board.forEach(function(v){ boardsEl.appendChild(venuePanel(v)); });
  }

  function venuePanel(v){
    var venue = v.venue;
    var st = v.state || {};
    var isActive = venue.active !== 0 && venue.active !== false;
    var stateName = st.state || 'IDLE';

    var p = document.createElement('section');
    p.className = 'panel';
    p.dataset.venue = venue.id;

    p.innerHTML =
      '<div class="row">' +
        '<h2>' + esc(venue.name) + '</h2>' +
        '<span class="pill ' + (isActive ? 'ok' : 'err') + '">' + (isActive ? 'Active' : 'Inactive') + '</span>' +
        '<span class="state-pill state-' + esc(stateName) + '">' + esc(stateName) + '</span>' +
      '</div>' +
      '<form class="stage-control-form">' +
        '<div class="split">' +
          '<label>Stage Active' +
            '<select name="active">' +
              '<option value="1"' + (isActive ? ' selected' : '') + '>Active</option>' +
              '<option value="0"' + (!isActive ? ' selected' : '') + '>Inactive</option>' +
            '</select>' +
          '</label>' +
          '<label>Stage Status' +
            '<select name="state">' +
              ['IDLE', 'RUNNING', 'PAUSED', 'BREAK', 'FINISHED'].map(function(s){
                return '<option' + (s === stateName ? ' selected' : '') + '>' + s + '</option>';
              }).join('') +
            '</select>' +
          '</label>' +
        '</div>' +
        '<label>Current Item (optional)' +
          '<input name="current_item" maxlength="200" placeholder="Not defined" value="' + esc(st.current_item || '') + '">' +
        '</label>' +
        '<div class="split">' +
          '<label>Current Chest Number (optional)' +
            '<input name="current_chest" maxlength="32" placeholder="Not defined" value="' + esc(st.current_chest || '') + '">' +
          '</label>' +
          '<label>Upcoming Chest Numbers (optional)' +
            '<input name="upcoming_chests" maxlength="280" placeholder="Not defined (e.g. 105, 106, 107)" value="' + esc(st.upcoming_chests || '') + '">' +
          '</label>' +
        '</div>' +
        '<label>Announcements (optional)' +
          '<textarea name="announcement" rows="2" maxlength="280" placeholder="No announcement">' + esc(st.announcement || '') + '</textarea>' +
        '</label>' +
        '<div class="row" style="margin-top:.9rem">' +
          '<button type="submit" class="primary">Save Stage</button>' +
        '</div>' +
      '</form>';

    var form = p.querySelector('form');
    form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      lastAction[venue.id] = Date.now();
      try {
        var r = await A.api('/api/v1/live/state', {
          method: 'POST',
          body: {
            venue_id: Number(venue.id),
            active: form.elements.active.value === '1',
            state: form.elements.state.value,
            current_item: form.elements.current_item.value.trim() || null,
            current_chest: form.elements.current_chest.value.trim() || null,
            upcoming_chests: form.elements.upcoming_chests.value.trim() || null,
            announcement: form.elements.announcement.value.trim()
          }
        });
        if (!r.ok){
          A.toast('Save failed: ' + (r.detail || r.status), true);
          return;
        }
        A.toast(venue.name + ' updated.');
        await loadBoard();
      } finally {
        btn.disabled = false;
      }
    });
    return p;
  }

  // ── Photo Preview & Removal Helpers ───────────────────────────────────────
  function renderPreview(key, containerId){
    previewUrls[key].forEach(function(u){ try { URL.revokeObjectURL(u); } catch(e){} });
    previewUrls[key] = [];
    var box = document.getElementById(containerId);
    if (!box) return;
    box.innerHTML = photoFiles[key].map(function(f, idx){
      var u = URL.createObjectURL(f);
      previewUrls[key].push(u);
      return '<div class="photo-thumb">' +
        '<img src="' + u + '" alt="' + esc(f.name) + '">' +
        '<button type="button" class="rm-btn" data-rm-key="' + key + '" data-rm-idx="' + idx + '" title="Remove photo">&times;</button>' +
        '<div class="meta">' + esc(f.name) + '</div>' +
      '</div>';
    }).join('');
  }

  function appendFiles(key, containerId, fileList){
    var added = Array.from(fileList || []);
    for (var i = 0; i < added.length; i++){
      var f = added[i];
      if (f.size > 10 * 1024 * 1024){
        A.toast('Skipped ' + f.name + ' (exceeds 10 MB)', true);
        continue;
      }
      photoFiles[key].push(f);
    }
    renderPreview(key, containerId);
  }

  // ── Workflow 2 Register Number Chips & Suggestions ────────────────────────
  function renderRegChips(){
    var box = document.getElementById('w2-reg-chips');
    if (!box) return;
    box.innerHTML = w2SelectedRegs.map(function(item, idx){
      return '<span class="chip">' +
        '<strong>' + esc(item.register_no) + '</strong>' +
        (item.name ? ' · ' + esc(item.name) : '') +
        '<button type="button" data-rm-reg="' + idx + '" title="Remove">&times;</button>' +
      '</span>';
    }).join('');
  }

  function addRegChip(reg, name){
    reg = String(reg || '').trim();
    if (!/^\d{4,5}$/.test(reg)){
      A.toast('Register number must be 4 or 5 digits.', true);
      return;
    }
    if (w2SelectedRegs.some(function(x){ return x.register_no === reg; })) return;
    w2SelectedRegs.push({ register_no: reg, name: name || '' });
    renderRegChips();
  }

  function currentW2ItemCode(){
    var sel = document.getElementById('w2-item');
    var custom = document.getElementById('w2-item-custom');
    if (!sel) return '';
    return sel.value === '__custom__' ? (custom ? custom.value.trim() : '') : sel.value.trim();
  }

  async function fetchSuggestions(query, itemCode){
    var params = [];
    if (query && query.length >= 2) params.push('q=' + encodeURIComponent(query));
    if (itemCode) params.push('item_code=' + encodeURIComponent(itemCode));
    var sugBox = document.getElementById('w2-reg-suggestions');
    if (!params.length){ if (sugBox) sugBox.innerHTML = ''; return; }
    var r = await A.api('/api/v1/photos/participants/search?' + params.join('&'));
    if (!r.ok || !sugBox) return;
    var parts = r.data.participants || [];
    sugBox.innerHTML = parts.slice(0, 8).map(function(p){
      return '<button type="button" class="small" style="margin:.15rem .3rem .15rem 0" ' +
        'data-pick-reg="' + esc(p.register_no) + '" data-pick-name="' + esc(p.name) + '">' +
        '+ ' + esc(p.register_no) + ' · ' + esc(p.name) + '</button>';
    }).join('') || '<span class="muted xs">No matching registered students.</span>';
  }

  // ── Photo Upload Execution ────────────────────────────────────────────────
  async function uploadBulk(btn){
    var venueId = Number(document.getElementById('photo-venue-select').value);
    if (!venueId){ A.toast('Select a stage first.', true); return; }
    var files = photoFiles.w1Slips.map(function(f){ return { kind: 'slip', file: f }; })
      .concat(photoFiles.w1Stage.map(function(f){ return { kind: 'stage', file: f }; }));
    if (!files.length){ A.toast('Add at least one photo first.', true); return; }

    btn.disabled = true;
    try {
      var batchReq = await A.api('/api/v1/photos/batches', {
        method: 'POST',
        body: { venue_id: venueId, workflow: 'bulk', perf_date: new Date().toISOString().split('T')[0] }
      });
      if (!batchReq.ok){ A.toast('Batch error: ' + (batchReq.detail || batchReq.status), true); return; }
      var batchId = batchReq.data.batch_id;
      A.toast('Uploading ' + files.length + ' photo(s)…');

      for (var i = 0; i < files.length; i++){
        var fd = new FormData();
        fd.append('kind', files[i].kind);
        fd.append('file', files[i].file);
        var up = await A.api('/api/v1/photos/batches/' + batchId + '/upload', { method: 'POST', body: fd });
        if (!up.ok){ A.toast('Upload failed: ' + (up.detail || up.status), true); return; }
      }
      photoFiles.w1Slips = [];
      photoFiles.w1Stage = [];
      renderPreview('w1Slips', 'w1-slips-preview');
      renderPreview('w1Stage', 'w1-stage-preview');
      A.toast('Queued batch #' + batchId + ' for Data Worker.');
    } finally {
      btn.disabled = false;
    }
  }

  async function uploadQuick(btn){
    var venueId = Number(document.getElementById('photo-venue-select').value);
    var itemCode = currentW2ItemCode();
    if (!venueId){ A.toast('Select a stage first.', true); return; }
    if (!itemCode){ A.toast('Select or enter an item first.', true); return; }
    if (!w2SelectedRegs.length){ A.toast('Add at least one register number.', true); return; }
    if (!photoFiles.w2Stage.length){ A.toast('Add at least one stage photo.', true); return; }

    var regs = w2SelectedRegs.map(function(x){ return x.register_no; });
    var today = new Date().toISOString().split('T')[0];

    btn.disabled = true;
    try {
      var batchReq = await A.api('/api/v1/photos/batches', {
        method: 'POST',
        body: { venue_id: venueId, workflow: 'quick', perf_date: today }
      });
      if (!batchReq.ok){ A.toast('Batch error: ' + (batchReq.detail || batchReq.status), true); return; }
      var batchId = batchReq.data.batch_id;
      A.toast('Uploading & assigning ' + photoFiles.w2Stage.length + ' photo(s)…');

      for (var i = 0; i < photoFiles.w2Stage.length; i++){
        var fd = new FormData();
        fd.append('kind', 'stage');
        fd.append('file', photoFiles.w2Stage[i]);
        var up = await A.api('/api/v1/photos/batches/' + batchId + '/upload', { method: 'POST', body: fd });
        if (!up.ok){ A.toast('Upload failed: ' + (up.detail || up.status), true); return; }

        var asg = await A.api('/api/v1/photos/assign-by-register', {
          method: 'POST',
          body: {
            asset_id: up.data.asset_id,
            venue_id: venueId,
            item_code: itemCode,
            register_nos: regs,
            perf_date: today
          }
        });
        if (!asg.ok){ A.toast('Assign failed: ' + (asg.detail || asg.status), true); return; }
      }

      var pub = await A.api('/api/v1/photos/batches/' + batchId + '/publish', { method: 'POST' });
      if (!pub.ok){ A.toast('Publish failed', true); return; }

      photoFiles.w2Stage = [];
      renderPreview('w2Stage', 'w2-stage-preview');
      A.toast('Uploaded & published ' + regs.join(', ') + ' (' + itemCode + ').');
    } finally {
      btn.disabled = false;
    }
  }

  function startFeed(){
    if (feed) feed.close();
    feed = A.stream('/api/v1/live/stream', {
      onopen: function(){ connEl.textContent = 'live'; connEl.className = 'badge live'; },
      onmissed: function(){ connEl.textContent = 'reconnecting…'; connEl.className = 'badge offline'; },
      '*': function(msg){
        if (msg.venue_id && lastAction[msg.venue_id] && Date.now() - lastAction[msg.venue_id] < 1200) return;
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
    loadSchedule();
    startFeed();
  };

  document.addEventListener('DOMContentLoaded', function(){
    boardsEl = document.getElementById('boards');
    connEl = document.getElementById('conn');
    whoEl = document.getElementById('who');

    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('sync-btn').addEventListener('click', loadBoard);

    document.getElementById('w1-slips').addEventListener('change', function(){
      appendFiles('w1Slips', 'w1-slips-preview', this.files); this.value = '';
    });
    document.getElementById('w1-stage').addEventListener('change', function(){
      appendFiles('w1Stage', 'w1-stage-preview', this.files); this.value = '';
    });
    document.getElementById('w2-stage').addEventListener('change', function(){
      appendFiles('w2Stage', 'w2-stage-preview', this.files); this.value = '';
    });

    document.getElementById('photo-intake').addEventListener('click', function(ev){
      var rmPhoto = ev.target.closest('[data-rm-key]');
      if (rmPhoto){
        var k = rmPhoto.dataset.rmKey;
        photoFiles[k].splice(Number(rmPhoto.dataset.rmIdx), 1);
        var map = { w1Slips: 'w1-slips-preview', w1Stage: 'w1-stage-preview', w2Stage: 'w2-stage-preview' };
        renderPreview(k, map[k]);
        return;
      }
      var pickReg = ev.target.closest('[data-pick-reg]');
      if (pickReg){
        addRegChip(pickReg.dataset.pickReg, pickReg.dataset.pickName);
        return;
      }
      var rmReg = ev.target.closest('[data-rm-reg]');
      if (rmReg){
        w2SelectedRegs.splice(Number(rmReg.dataset.rmReg), 1);
        renderRegChips();
      }
    });

    var w2ItemSel = document.getElementById('w2-item');
    var w2Custom = document.getElementById('w2-item-custom');
    if (w2ItemSel){
      w2ItemSel.addEventListener('change', function(){
        if (w2Custom) w2Custom.style.display = this.value === '__custom__' ? 'block' : 'none';
        fetchSuggestions(document.getElementById('w2-reg-search').value.trim(), currentW2ItemCode());
      });
    }

    var sugTmr;
    var regSearch = document.getElementById('w2-reg-search');
    if (regSearch){
      regSearch.addEventListener('input', function(){
        clearTimeout(sugTmr);
        var q = this.value.trim();
        sugTmr = setTimeout(function(){ fetchSuggestions(q, currentW2ItemCode()); }, 240);
      });
      regSearch.addEventListener('keydown', function(ev){
        if (ev.key === 'Enter'){
          ev.preventDefault();
          if (/^\d{4,5}$/.test(this.value.trim())){ addRegChip(this.value.trim(), ''); this.value = ''; }
        }
      });
    }

    document.getElementById('w2-reg-add').addEventListener('click', function(){
      var val = regSearch ? regSearch.value.trim() : '';
      if (/^\d{4,5}$/.test(val)){ addRegChip(val, ''); regSearch.value = ''; }
      else A.toast('Type a 4-5 digit register number or pick from suggestions.', true);
    });

    document.getElementById('w1-submit').addEventListener('click', function(){ uploadBulk(this); });
    document.getElementById('w2-submit').addEventListener('click', function(){ uploadQuick(this); });

    window.KalAuth.init();
  });
})();
