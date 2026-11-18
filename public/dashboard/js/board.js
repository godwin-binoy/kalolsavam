(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var boardsEl, connEl, whoEl;
  var feed = null;
  var boardData = [];
  var scheduleEvents = [];
  var lastAction = {};
  var syncTimer = null;

  var photoFiles = { w1Slips: [], w1Stage: [], w2Stage: [] };
  var previewUrls = { w1Slips: [], w1Stage: [], w2Stage: [] };
  var w2SelectedRegs = [];
  var w2ItemCode = '';

  async function loadSchedule(){
    var r = await A.api('/api/v1/public/schedule');
    if (r.ok && r.data && Array.isArray(r.data.events)){
      scheduleEvents = r.data.events;
    }
  }

  function renderMenu(menuEl, rowsHtml){
    if (!menuEl) return;
    if (!rowsHtml){
      menuEl.classList.add('hidden');
      menuEl.innerHTML = '';
      return;
    }
    menuEl.innerHTML = rowsHtml;
    menuEl.classList.remove('hidden');
  }

  function filterEvents(query, venueName){
    var q = (query || '').trim().toLowerCase();
    var vLow = (venueName || '').toLowerCase();
    var list = scheduleEvents.slice();
    list.sort(function(a, b){
      var aMatch = vLow && a.venue && a.venue.toLowerCase() === vLow ? 0 : 1;
      var bMatch = vLow && b.venue && b.venue.toLowerCase() === vLow ? 0 : 1;
      return aMatch - bMatch;
    });
    if (q){
      var tokens = q.split(/\s+/).filter(Boolean);
      list = list.filter(function(e){
        var hay = (e.code + ' ' + e.title + ' ' + (e.category || '') + ' ' + (e.venue || '') + ' ' + (e.day || '')).toLowerCase();
        return tokens.every(function(t){ return hay.indexOf(t) >= 0; });
      });
    }
    return list.slice(0, 12);
  }

  async function searchParticipants(query, itemCode){
    var params = [];
    if (query) params.push('q=' + encodeURIComponent(query));
    if (itemCode) params.push('item_code=' + encodeURIComponent(itemCode));
    if (!params.length) return [];
    var r = await A.api('/api/v1/photos/participants/search?' + params.join('&'));
    return (r.ok && r.data && r.data.participants) ? r.data.participants : [];
  }

  async function fetchTeamForRegister(reg, itemCode){
    reg = String(reg || '').trim();
    if (!/^\d{4,5}$/.test(reg)) return null;
    var url = '/api/v1/photos/team-lookup?register_no=' + encodeURIComponent(reg) +
      (itemCode ? '&item_code=' + encodeURIComponent(itemCode) : '');
    var r = await A.api(url);
    return r.ok ? r.data : null;
  }

  async function loadBoard(force){
    if (!force && boardsEl && boardsEl.contains(document.activeElement)){
      var tag = (document.activeElement.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    }
    var r = await A.api('/api/v1/live/board');
    if (!r.ok){
      if (r.status === 401) return;
      if (r.status === 403){
        boardsEl.innerHTML = '<div class="panel"><p class="err">Access denied for Stage Control. Please sign in with a stagemaster or admin account.</p></div>';
        return;
      }
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
    var uid = String(venue.id);

    var p = document.createElement('section');
    p.className = 'panel';
    p.dataset.venue = uid;

    p.innerHTML =
      '<div class="row">' +
        '<h2>' + esc(venue.name) + '</h2>' +
        '<span class="pill ' + (isActive ? 'ok' : 'err') + '">' + (isActive ? 'Active' : 'Inactive') + '</span>' +
        '<span class="state-pill state-' + esc(stateName) + '">' + esc(stateName) + '</span>' +
      '</div>' +
      '<form class="stage-control-form">' +
        '<div class="split">' +
          '<div class="field"><label for="act-' + uid + '">Stage Active</label>' +
            '<select id="act-' + uid + '" name="active">' +
              '<option value="1"' + (isActive ? ' selected' : '') + '>Active</option>' +
              '<option value="0"' + (!isActive ? ' selected' : '') + '>Inactive</option>' +
            '</select>' +
          '</div>' +
          '<div class="field"><label for="st-' + uid + '">Stage Status</label>' +
            '<select id="st-' + uid + '" name="state">' +
              ['IDLE', 'RUNNING', 'PAUSED', 'BREAK', 'FINISHED'].map(function(s){
                return '<option' + (s === stateName ? ' selected' : '') + '>' + s + '</option>';
              }).join('') +
            '</select>' +
          '</div>' +
        '</div>' +
        '<div class="field"><label for="ci-' + uid + '">Current Item (type to search DB)</label>' +
          '<div class="ac-wrap">' +
            '<input id="ci-' + uid + '" name="current_item" maxlength="200" autocomplete="off" placeholder="Start typing item name or code…" value="' + esc(st.current_item || '') + '">' +
            '<div class="ac-menu hidden" data-menu="item"></div>' +
          '</div>' +
        '</div>' +
        '<div class="split">' +
          '<div class="field"><label for="cc-' + uid + '">Current Chest / Reg No</label>' +
            '<div class="ac-wrap">' +
              '<input id="cc-' + uid + '" name="current_chest" maxlength="32" autocomplete="off" placeholder="Reg no, student, or school…" value="' + esc(st.current_chest || '') + '">' +
              '<div class="ac-menu hidden" data-menu="chest"></div>' +
            '</div>' +
          '</div>' +
          '<div class="field"><label for="uc-' + uid + '">Upcoming Chest Numbers</label>' +
            '<div class="ac-wrap">' +
              '<input id="uc-' + uid + '" name="upcoming_chests" maxlength="280" autocomplete="off" placeholder="Comma-separated e.g. 1054, 1082" value="' + esc(st.upcoming_chests || '') + '">' +
              '<div class="ac-menu hidden" data-menu="upcoming"></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div class="quick-pills">' +
          '<button type="button" class="quick-pill" data-next-chest>Next Chest &rarr;</button>' +
          '<button type="button" class="quick-pill" data-ann="Reporting now — participants check in at stage">Reporting Now</button>' +
          '<button type="button" class="quick-pill" data-ann="Short 5 min break">5m Break</button>' +
          '<button type="button" class="quick-pill" data-ann="Lunch break">Lunch Break</button>' +
          '<button type="button" class="quick-pill" data-ann="">Clear Notice</button>' +
        '</div>' +
        '<div class="field"><label for="ann-' + uid + '">Announcements (optional)</label>' +
          '<textarea id="ann-' + uid + '" name="announcement" rows="2" maxlength="280" placeholder="No announcement">' + esc(st.announcement || '') + '</textarea>' +
        '</div>' +
        '<div class="row" style="margin-top:.9rem">' +
          '<button type="submit" class="primary">Save Stage</button>' +
        '</div>' +
      '</form>';

    var form = p.querySelector('form');
    var itemInp = form.elements.current_item;
    var chestInp = form.elements.current_chest;
    var upInp = form.elements.upcoming_chests;
    var itemMenu = form.querySelector('[data-menu="item"]');
    var chestMenu = form.querySelector('[data-menu="chest"]');
    var upMenu = form.querySelector('[data-menu="upcoming"]');
    var selectedCode = '';

    function showItemSug(){
      var matches = filterEvents(itemInp.value, venue.name);
      renderMenu(itemMenu, matches.map(function(e){
        return '<button type="button" class="ac-item" data-pick-item="' + esc(e.title) + '" data-pick-code="' + esc(e.code) + '">' +
          '<span><strong>' + esc(e.title) + '</strong> <span class="muted">(' + esc(e.code) + ')</span></span>' +
          '<span class="xs muted">' + esc(e.scheduled_time || '') + '</span></button>';
      }).join(''));
    }
    itemInp.addEventListener('focus', showItemSug);
    itemInp.addEventListener('input', showItemSug);
    itemMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-pick-item]');
      if (!b) return;
      itemInp.value = b.dataset.pickItem;
      selectedCode = b.dataset.pickCode || '';
      itemMenu.classList.add('hidden');
    });

    var chestTimer;
    function showChestSug(){
      clearTimeout(chestTimer);
      var q = chestInp.value.trim();
      chestTimer = setTimeout(async function(){
        var parts = await searchParticipants(q, selectedCode);
        renderMenu(chestMenu, parts.slice(0, 10).map(function(pt){
          return '<button type="button" class="ac-item" data-pick-chest="' + esc(pt.register_no) + '">' +
            '<span><strong>' + esc(pt.register_no) + '</strong> · ' + esc(pt.name) + '</span>' +
            '<span class="xs muted">' + esc(pt.school_name) + '</span></button>';
        }).join(''));
      }, 180);
    }
    chestInp.addEventListener('focus', function(){ if (chestInp.value.trim() || selectedCode) showChestSug(); });
    chestInp.addEventListener('input', showChestSug);
    chestMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-pick-chest]');
      if (!b) return;
      chestInp.value = b.dataset.pickChest;
      chestMenu.classList.add('hidden');
    });

    var upTimer;
    function showUpSug(){
      clearTimeout(upTimer);
      var raw = upInp.value;
      var last = raw.split(/[,\s]+/).pop().trim();
      if (!last && !selectedCode){ upMenu.classList.add('hidden'); return; }
      upTimer = setTimeout(async function(){
        var parts = await searchParticipants(last, selectedCode);
        renderMenu(upMenu, parts.slice(0, 10).map(function(pt){
          return '<button type="button" class="ac-item" data-pick-up="' + esc(pt.register_no) + '">' +
            '<span><strong>' + esc(pt.register_no) + '</strong> · ' + esc(pt.name) + '</span>' +
            '<span class="xs muted">' + esc(pt.school_name) + '</span></button>';
        }).join(''));
      }, 180);
    }
    upInp.addEventListener('input', showUpSug);
    upMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-pick-up]');
      if (!b) return;
      var existing = upInp.value.split(/[,\s]+/).map(function(x){ return x.trim(); }).filter(Boolean);
      var typedLast = upInp.value.slice(-1) !== ',' && upInp.value.slice(-1) !== ' ' && existing.length ? existing.pop() : null;
      if (typedLast && /^\d{4,5}$/.test(typedLast)) existing.push(typedLast);
      if (existing.indexOf(b.dataset.pickUp) < 0) existing.push(b.dataset.pickUp);
      upInp.value = existing.join(', ');
      upMenu.classList.add('hidden');
    });

    p.querySelector('[data-next-chest]').addEventListener('click', function(){
      var tokens = upInp.value.split(/[\s,;]+/).map(function(x){ return x.trim(); }).filter(Boolean);
      if (!tokens.length){ A.toast('No upcoming chests in queue.', true); return; }
      chestInp.value = tokens.shift();
      upInp.value = tokens.join(', ');
      form.elements.state.value = 'RUNNING';
      form.requestSubmit();
    });
    p.querySelectorAll('[data-ann]').forEach(function(btn){
      btn.addEventListener('click', function(){
        form.elements.announcement.value = btn.getAttribute('data-ann') || '';
      });
    });

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
            current_item: itemInp.value.trim() || null,
            current_chest: chestInp.value.trim() || null,
            upcoming_chests: upInp.value.trim() || null,
            announcement: form.elements.announcement.value.trim()
          }
        });
        if (!r.ok){
          A.toast('Save failed: ' + (r.detail || r.status), true);
          return;
        }
        A.toast(venue.name + ' updated.');
        await loadBoard(true);
      } finally {
        btn.disabled = false;
      }
    });
    return p;
  }

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
    if (!/^\d{4,5}$/.test(reg)) return false;
    if (w2SelectedRegs.some(function(x){ return x.register_no === reg; })) return true;
    w2SelectedRegs.push({ register_no: reg, name: name || '' });
    renderRegChips();
    return true;
  }

  async function autoFetchSchoolTeam(reg){
    var data = await fetchTeamForRegister(reg, w2ItemCode);
    var banner = document.getElementById('w2-team-banner');
    if (!data){
      A.toast('Register #' + reg + ' not found in database.', true);
      return;
    }
    var team = data.team || [];
    team.forEach(function(m){ addRegChip(m.register_no, m.name); });
    if (banner){
      banner.innerHTML = 'School: <strong>' + esc(data.school_name) + '</strong> · Added <strong>' + team.length + '</strong> participant(s)' +
        (data.school_peers && data.school_peers.length > team.length
          ? ' <button type="button" class="quick-pill" id="w2-add-all-school">Add all ' + data.school_peers.length + ' from school</button>'
          : '');
      var addAll = document.getElementById('w2-add-all-school');
      if (addAll){
        addAll.addEventListener('click', function(){
          data.school_peers.forEach(function(m){ addRegChip(m.register_no, m.name); });
          A.toast('Added all ' + data.school_peers.length + ' students from ' + data.school_name);
        });
      }
    }
  }

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
    var itemInput = document.getElementById('w2-item-input');
    var code = w2ItemCode || (itemInput ? itemInput.value.trim() : '');
    if (!venueId){ A.toast('Select a stage first.', true); return; }
    if (!code){ A.toast('Select or type an item first.', true); return; }
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
            item_code: code,
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
      A.toast('Published to ' + regs.join(', ') + '!');
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
        clearTimeout(syncTimer);
        syncTimer = setTimeout(function(){ loadBoard(false); }, 300);
      }
    });
  }

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    var lc = document.querySelector('.login-card'); if (lc) lc.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    whoEl.textContent = (info.username || info.email || 'staff') + ' · ' + (info.role || 'stagemaster');
    loadBoard(true);
    loadSchedule();
    startFeed();
  };

  document.addEventListener('DOMContentLoaded', function(){
    boardsEl = document.getElementById('boards');
    connEl = document.getElementById('conn');
    whoEl = document.getElementById('who');

    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('sync-btn').addEventListener('click', function(){ loadBoard(true); });

    document.getElementById('w1-slips').addEventListener('change', function(){
      appendFiles('w1Slips', 'w1-slips-preview', this.files); this.value = '';
    });
    document.getElementById('w1-stage').addEventListener('change', function(){
      appendFiles('w1Stage', 'w1-stage-preview', this.files); this.value = '';
    });
    document.getElementById('w2-stage').addEventListener('change', function(){
      appendFiles('w2Stage', 'w2-stage-preview', this.files); this.value = '';
    });

    var w2ItemInp = document.getElementById('w2-item-input');
    var w2ItemMenu = document.getElementById('w2-item-menu');
    var w2ItemPicked = document.getElementById('w2-item-picked');
    function showW2ItemSug(){
      var vid = Number(document.getElementById('photo-venue-select').value);
      var vObj = boardData.find(function(b){ return b.venue.id === vid; });
      var matches = filterEvents(w2ItemInp.value, vObj ? vObj.venue.name : '');
      renderMenu(w2ItemMenu, matches.map(function(e){
        return '<button type="button" class="ac-item" data-w2-code="' + esc(e.code) + '" data-w2-title="' + esc(e.title) + '">' +
          '<span><strong>' + esc(e.title) + '</strong> <span class="muted">(' + esc(e.code) + ')</span></span>' +
          '<span class="xs muted">' + esc(e.venue || '') + '</span></button>';
      }).join(''));
    }
    w2ItemInp.addEventListener('focus', showW2ItemSug);
    w2ItemInp.addEventListener('input', function(){
      w2ItemCode = '';
      if (w2ItemPicked) w2ItemPicked.textContent = '';
      showW2ItemSug();
    });
    w2ItemMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-w2-code]');
      if (!b) return;
      w2ItemCode = b.dataset.w2Code;
      w2ItemInp.value = b.dataset.w2Title + ' (' + w2ItemCode + ')';
      if (w2ItemPicked) w2ItemPicked.textContent = 'Item code: ' + w2ItemCode;
      w2ItemMenu.classList.add('hidden');
    });

    document.getElementById('w2-use-current-item').addEventListener('click', function(){
      var vid = Number(document.getElementById('photo-venue-select').value);
      var b = boardData.find(function(x){ return x.venue.id === vid; });
      var cur = b && b.state && b.state.current_item;
      if (!cur){ A.toast('No item currently set on stage.', true); return; }
      var evObj = scheduleEvents.find(function(e){ return e.title.toLowerCase() === cur.toLowerCase(); });
      w2ItemCode = evObj ? evObj.code : cur;
      w2ItemInp.value = evObj ? (evObj.title + ' (' + evObj.code + ')') : cur;
      if (w2ItemPicked) w2ItemPicked.textContent = 'Item code: ' + w2ItemCode;
    });
    document.getElementById('w2-use-current-chest').addEventListener('click', function(){
      var vid = Number(document.getElementById('photo-venue-select').value);
      var b = boardData.find(function(x){ return x.venue.id === vid; });
      var ch = b && b.state && b.state.current_chest;
      if (!ch){ A.toast('No chest number currently set on stage.', true); return; }
      autoFetchSchoolTeam(ch);
    });
    document.getElementById('w2-clear-regs').addEventListener('click', function(){
      w2SelectedRegs = [];
      renderRegChips();
      var ban = document.getElementById('w2-team-banner');
      if (ban) ban.textContent = '';
    });

    var regSearch = document.getElementById('w2-reg-search');
    var regMenu = document.getElementById('w2-reg-menu');
    var regTimer;
    async function showRegSug(){
      clearTimeout(regTimer);
      var q = regSearch.value.trim();
      if (!q && !w2ItemCode){ regMenu.classList.add('hidden'); return; }
      regTimer = setTimeout(async function(){
        var parts = await searchParticipants(q, w2ItemCode);
        renderMenu(regMenu, parts.slice(0, 12).map(function(pt){
          return '<button type="button" class="ac-item" data-pick-reg="' + esc(pt.register_no) + '" data-pick-name="' + esc(pt.name) + '">' +
            '<span><strong>' + esc(pt.register_no) + '</strong> · ' + esc(pt.name) + '</span>' +
            '<span class="xs muted">' + esc(pt.school_name) + '</span></button>';
        }).join(''));
      }, 180);
    }
    regSearch.addEventListener('input', showRegSug);
    regSearch.addEventListener('focus', function(){ if (regSearch.value.trim() || w2ItemCode) showRegSug(); });
    regMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-pick-reg]');
      if (!b) return;
      regMenu.classList.add('hidden');
      regSearch.value = '';
      autoFetchSchoolTeam(b.dataset.pickReg);
    });
    regSearch.addEventListener('keydown', function(ev){
      if (ev.key === 'Enter'){
        ev.preventDefault();
        var v = regSearch.value.trim();
        if (/^\d{4,5}$/.test(v)){
          regMenu.classList.add('hidden');
          regSearch.value = '';
          autoFetchSchoolTeam(v);
        }
      }
    });
    document.getElementById('w2-fetch-team').addEventListener('click', function(){
      var v = regSearch.value.trim();
      if (/^\d{4,5}$/.test(v)){
        regMenu.classList.add('hidden');
        regSearch.value = '';
        autoFetchSchoolTeam(v);
      } else {
        A.toast('Enter a 4–5 digit register number first.', true);
      }
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
      var rmReg = ev.target.closest('[data-rm-reg]');
      if (rmReg){
        w2SelectedRegs.splice(Number(rmReg.dataset.rmReg), 1);
        renderRegChips();
      }
    });

    document.addEventListener('click', function(ev){
      document.querySelectorAll('.ac-wrap').forEach(function(wrap){
        if (!wrap.contains(ev.target)){
          var m = wrap.querySelector('.ac-menu');
          if (m) m.classList.add('hidden');
        }
      });
    });

    document.getElementById('w1-submit').addEventListener('click', function(){ uploadBulk(this); });
    document.getElementById('w2-submit').addEventListener('click', function(){ uploadQuick(this); });

    window.KalAuth.init();
  });
})();
