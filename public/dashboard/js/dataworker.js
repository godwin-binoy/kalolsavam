(function(){
  'use strict';
  var A = window.KalAPI, K = window.Kal, esc = A.esc, el = A.el;
  var view, detailView, detailContent, liveStrip, dwConn;
  var blobUrls = [], curStatus = 'queued', curBatchId = null, curBatchVenueId = null;
  var scheduleEvents = [], liveFeed = null, livePollTimer = null;
  var batchTeamRegs = [], batchItemCode = '';

  function revokeBlobs(){ blobUrls.forEach(function(u){ try { URL.revokeObjectURL(u); } catch(e){} }); blobUrls = []; }

  async function loadImageInto(img, apiPath){
    try {
      var res = await A.authorizedFetch(apiPath, { method: 'GET' });
      if (!res.ok) return;
      var u = URL.createObjectURL(await res.blob());
      blobUrls.push(u); img.src = u;
    } catch(e){}
  }

  async function loadSchedule(){
    var r = await A.api('/api/v1/public/schedule');
    if (r.ok && r.data && Array.isArray(r.data.events)) scheduleEvents = r.data.events;
  }

  async function refreshLiveStages(){
    try {
      var d = await K.fetchJSON('/api/v1/public/status');
      var STAGE_IDS = { 1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:1, 26:1 };
      var venues = ((d && d.venues) || []).filter(function(v){ return STAGE_IDS[Number(v.id)]; });
      if (!liveStrip) return;
      liveStrip.innerHTML = venues.map(function(v){
        var st = String(v.state || 'IDLE');
        var cls = st === 'RUNNING' ? 'running' : ((st === 'PAUSED' || st === 'BREAK') ? 'paused' : '');
        var nowTxt = v.now ? ((v.now.roll ? ('#' + esc(v.now.roll) + ' · ') : '') + esc(v.now.event || 'On stage')) : 'Idle';
        var upTxt = (v.upcoming && v.upcoming.length) ? ('Next: ' + v.upcoming.slice(0, 3).map(function(u){ return '#' + esc(u.roll); }).join(', ')) : '';
        return '<div class="live-mini ' + cls + '">' +
          '<div class="row" style="justify-content:space-between;gap:.4rem">' +
            '<strong>' + esc(v.name) + '</strong>' +
            '<span class="pill ' + (st === 'RUNNING' ? 'ok' : (st === 'PAUSED' || st === 'BREAK' ? 'warn' : '')) + '">' + esc(st) + '</span>' +
          '</div>' +
          '<div style="margin-top:.25rem">' + nowTxt + '</div>' +
          (upTxt ? '<div class="xs muted" style="margin-top:.15rem">' + upTxt + '</div>' : '') +
          (v.announcement ? '<div class="xs" style="color:var(--accent);margin-top:.15rem">' + esc(v.announcement) + '</div>' : '') +
        '</div>';
      }).join('') || '<p class="muted small">No live stage updates available.</p>';
    } catch(e){}
  }

  function startLiveUpdates(){
    refreshLiveStages();
    if (livePollTimer) clearInterval(livePollTimer);
    livePollTimer = setInterval(function(){ if (!document.hidden) refreshLiveStages(); }, 12000);
    if (liveFeed) liveFeed.close();
    liveFeed = A.stream('/api/v1/live/stream', {
      onopen: function(){ if (dwConn){ dwConn.textContent = 'live'; dwConn.className = 'badge live'; } },
      onmissed: function(){ if (dwConn){ dwConn.textContent = 'polling'; dwConn.className = 'badge offline'; } },
      '*': function(){ refreshLiveStages(); }
    });
  }

  async function loadBatches(){
    revokeBlobs();
    curBatchId = null;
    el('dw-publish-top').classList.add('hidden');
    view.innerHTML = '<div class="panel"><p class="muted">Loading batches…</p></div>';
    var d = await A.req('/api/v1/photos/batches?status=' + encodeURIComponent(curStatus));
    if (!d){ view.innerHTML = '<div class="panel"><p class="err">Failed to load batches.</p></div>'; return; }
    var batches = d.batches || [];
    view.innerHTML = batches.length ? batches.map(function(b){
      return '<div class="panel">' +
        '<div class="row" style="justify-content:space-between">' +
          '<h3>Batch #' + b.id + ' · ' + esc(b.venue_name || ('Stage ' + b.venue_id)) + '</h3>' +
          '<span class="pill ' + (b.status === 'published' ? 'ok' : 'warn') + '">' + esc(b.status) + '</span>' +
        '</div>' +
        '<p class="small muted">' + (b.slip_count || 0) + ' slip(s) · ' + (b.stage_count || 0) + ' stage photo(s) · ' +
          '<strong>' + (b.assigned_stage_count || 0) + ' / ' + (b.stage_count || 0) + ' assigned</strong>' +
          (b.perf_date ? ' · ' + esc(b.perf_date) : '') + '</p>' +
        '<button class="primary" data-open-batch="' + b.id + '">' + (b.status === 'published' ? 'Inspect / Edit' : 'Process Batch') + '</button>' +
      '</div>';
    }).join('') : '<div class="panel"><p class="muted">No ' + esc(curStatus) + ' batches.</p></div>';
  }

  function renderBatchChips(){
    var box = el('dw-team-chips');
    if (!box) return;
    box.innerHTML = batchTeamRegs.map(function(m, idx){
      return '<span class="chip"><strong>' + esc(m.register_no) + '</strong>' + (m.name ? ' · ' + esc(m.name) : '') +
        '<button type="button" data-dw-rm-chip="' + idx + '">&times;</button></span>';
    }).join('');
  }

  function addBatchChip(reg, name){
    reg = String(reg || '').trim();
    if (!/^\d{4,5}$/.test(reg)) return;
    if (batchTeamRegs.some(function(x){ return x.register_no === reg; })) return;
    batchTeamRegs.push({ register_no: reg, name: name || '' });
    renderBatchChips();
  }

  async function openBatch(id){
    revokeBlobs();
    curBatchId = id;
    batchTeamRegs = [];
    batchItemCode = '';
    view.classList.add('hidden');
    detailView.classList.remove('hidden');
    detailContent.innerHTML = '<div class="panel"><p class="muted">Loading batch #' + id + '…</p></div>';

    var d = await A.req('/api/v1/photos/batches/' + id);
    if (!d){ detailContent.innerHTML = '<div class="panel"><p class="err">Load failed.</p></div>'; return; }
    var batch = d.batch || {};
    curBatchVenueId = batch.venue_id;
    var pubTop = el('dw-publish-top');
    pubTop.classList.remove('hidden');
    pubTop.textContent = batch.status === 'published' ? '✔ Re-publish Batch #' + id : '✔ Publish Batch #' + id;

    var assets = d.assets || [];
    var slips = assets.filter(function(a){ return a.kind === 'slip'; });
    var stages = assets.filter(function(a){ return a.kind === 'stage'; });

    var slipsHtml = slips.length ? slips.map(function(s){
      return '<img data-auth-src="' + esc(s.url) + '" data-zoomable alt="Slip #' + s.id + '" style="width:100%;max-height:360px;object-fit:contain;border-radius:6px;margin-bottom:.75rem;border:1px solid var(--border);cursor:zoom-in;background:#000">';
    }).join('') : '<p class="muted small">No slip photos in this batch — check the Live Stage panel above for current chest &amp; item.</p>';

    var stagesHtml = stages.map(function(s){
      var isAssigned = (s.assigned_details || []).length > 0;
      var tags = (s.assigned_details || []).map(function(x){
        return '<span class="chip"><strong>' + esc(x.register_no) + '</strong> · ' + esc(x.name) +
          ' (' + esc(x.item_code) + ')' +
          '<button type="button" title="Remove tag" data-unassign-asset="' + s.id + '" data-unassign-entry="' + x.participant_entry_id + '">&times;</button></span>';
      }).join('');
      return '<div class="panel" style="margin-bottom:1rem">' +
        '<div class="row" style="justify-content:space-between;margin-bottom:.5rem">' +
          '<label style="margin:0;display:flex;align-items:center;gap:.45rem;font-weight:600;color:var(--text)">' +
            '<input type="checkbox" class="dw-photo-chk" value="' + s.id + '" data-assigned="' + (isAssigned ? '1' : '0') + '" style="width:auto;margin:0"> Photo #' + s.id +
          '</label>' +
          '<button type="button" class="danger small" data-del-asset="' + s.id + '">Delete Photo</button>' +
        '</div>' +
        '<img data-auth-src="' + esc(s.url) + '" data-zoomable alt="Stage #' + s.id + '" style="width:100%;max-height:300px;object-fit:contain;border-radius:6px;margin-bottom:.6rem;cursor:zoom-in;background:#000">' +
        '<div class="chip-list">' + (tags || '<span class="muted small">Unassigned</span>') + '</div>' +
        '<div class="row" style="margin-top:.5rem"><input type="search" data-search-asset="' + s.id + '" placeholder="Quick search reg no, name, or school…" style="flex:1"></div>' +
        '<div id="matches-' + s.id + '" style="margin-top:.4rem"></div>' +
      '</div>';
    }).join('');

    detailContent.innerHTML =
      '<div class="split" style="align-items:start">' +
        '<div class="sticky-col">' +
          '<div class="panel" style="margin-bottom:1rem">' +
            '<h2>Batch #' + id + ' · ' + esc(batch.venue_name || ('Stage ' + batch.venue_id)) + '</h2>' +
            '<h3 style="margin-top:.75rem">Slip Photos (' + slips.length + ')</h3>' +
            slipsHtml +
          '</div>' +
          '<div class="panel">' +
            '<h3>Quick School-Team Assign</h3>' +
            '<p class="xs muted">Enter the item and ONE register number to fetch the whole team from that school, then assign to selected or unassigned photos.</p>' +
            '<div class="field"><label for="dw-item-input">Competition Item</label>' +
              '<div class="ac-wrap">' +
                '<input id="dw-item-input" placeholder="Search item name or code…" autocomplete="off">' +
                '<div id="dw-item-menu" class="ac-menu hidden"></div>' +
              '</div>' +
            '</div>' +
            '<div class="field"><label for="dw-reg-input">One Register Number (fetches whole school team)</label>' +
              '<div class="row">' +
                '<div class="ac-wrap" style="flex:1">' +
                  '<input id="dw-reg-input" placeholder="Type reg no, name, or school…" autocomplete="off">' +
                  '<div id="dw-reg-menu" class="ac-menu hidden"></div>' +
                '</div>' +
                '<button type="button" id="dw-fetch-team" class="small primary">+ Team</button>' +
              '</div>' +
            '</div>' +
            '<div id="dw-team-info" class="xs muted" style="margin-top:.35rem"></div>' +
            '<div id="dw-team-chips" class="chip-list"></div>' +
            '<div class="row" style="margin-top:.75rem">' +
              '<button type="button" id="dw-sel-unassigned" class="small">Select Unassigned</button>' +
              '<button type="button" id="dw-sel-all" class="small">Select All</button>' +
              '<button type="button" id="dw-assign-checked" class="primary small">Assign to Selected</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div>' +
          '<h2>Stage Photos (' + stages.length + ')</h2>' +
          (stagesHtml || '<div class="panel"><p class="muted">No stage photos in this batch.</p></div>') +
        '</div>' +
      '</div>';

    detailContent.querySelectorAll('img[data-auth-src]').forEach(function(img){ loadImageInto(img, img.dataset.authSrc); });
    wireBatchToolbar();
  }

  function wireBatchToolbar(){
    var itemInp = el('dw-item-input'), itemMenu = el('dw-item-menu');
    var regInp = el('dw-reg-input'), regMenu = el('dw-reg-menu');
    if (!itemInp || !regInp) return;

    function showItemSug(){
      var q = itemInp.value.trim().toLowerCase();
      var tokens = q.split(/\s+/).filter(Boolean);
      var list = scheduleEvents.filter(function(e){
        var hay = (e.code + ' ' + e.title + ' ' + (e.category || '') + ' ' + (e.venue || '')).toLowerCase();
        return !tokens.length || tokens.every(function(t){ return hay.indexOf(t) >= 0; });
      }).slice(0, 12);
      if (!list.length){ itemMenu.classList.add('hidden'); return; }
      itemMenu.innerHTML = list.map(function(e){
        return '<button type="button" class="ac-item" data-dw-icode="' + esc(e.code) + '" data-dw-ititle="' + esc(e.title) + '">' +
          '<span><strong>' + esc(e.title) + '</strong> (' + esc(e.code) + ')</span>' +
          '<span class="xs muted">' + esc(e.venue || '') + '</span></button>';
      }).join('');
      itemMenu.classList.remove('hidden');
    }
    itemInp.addEventListener('focus', showItemSug);
    itemInp.addEventListener('input', function(){ batchItemCode = ''; showItemSug(); });
    itemMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-dw-icode]');
      if (!b) return;
      batchItemCode = b.dataset.dwIcode;
      itemInp.value = b.dataset.dwItitle + ' (' + batchItemCode + ')';
      itemMenu.classList.add('hidden');
    });

    async function fetchTeam(reg){
      var code = batchItemCode || itemInp.value.trim();
      var r = await A.api('/api/v1/photos/team-lookup?register_no=' + encodeURIComponent(reg) + (code ? '&item_code=' + encodeURIComponent(code) : ''));
      if (!r.ok){ A.toast('Participant #' + reg + ' not found.', true); return; }
      (r.data.team || []).forEach(function(m){ addBatchChip(m.register_no, m.name); });
      el('dw-team-info').innerHTML = 'School: <strong>' + esc(r.data.school_name) + '</strong> (' + (r.data.team || []).length + ' added)';
    }

    var regTimer;
    regInp.addEventListener('input', function(){
      clearTimeout(regTimer);
      var q = regInp.value.trim();
      if (!q && !batchItemCode){ regMenu.classList.add('hidden'); return; }
      regTimer = setTimeout(async function(){
        var r = await A.api('/api/v1/photos/participants/search?q=' + encodeURIComponent(q) + (batchItemCode ? '&item_code=' + encodeURIComponent(batchItemCode) : ''));
        var parts = (r.ok && r.data.participants) || [];
        if (!parts.length){ regMenu.classList.add('hidden'); return; }
        regMenu.innerHTML = parts.slice(0, 10).map(function(p){
          return '<button type="button" class="ac-item" data-dw-pick-reg="' + esc(p.register_no) + '">' +
            '<span><strong>' + esc(p.register_no) + '</strong> · ' + esc(p.name) + '</span>' +
            '<span class="xs muted">' + esc(p.school_name) + '</span></button>';
        }).join('');
        regMenu.classList.remove('hidden');
      }, 180);
    });
    regMenu.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-dw-pick-reg]');
      if (!b) return;
      regMenu.classList.add('hidden');
      regInp.value = '';
      fetchTeam(b.dataset.dwPickReg);
    });
    el('dw-fetch-team').addEventListener('click', function(){
      var v = regInp.value.trim();
      if (/^\d{4,5}$/.test(v)){ regInp.value = ''; fetchTeam(v); }
      else A.toast('Enter a 4–5 digit register number.', true);
    });

    el('dw-sel-unassigned').addEventListener('click', function(){
      detailContent.querySelectorAll('.dw-photo-chk').forEach(function(c){ c.checked = c.dataset.assigned === '0'; });
    });
    el('dw-sel-all').addEventListener('click', function(){
      detailContent.querySelectorAll('.dw-photo-chk').forEach(function(c){ c.checked = true; });
    });
    el('dw-assign-checked').addEventListener('click', async function(){
      var code = batchItemCode || itemInp.value.trim();
      var regs = batchTeamRegs.map(function(x){ return x.register_no; });
      var aids = Array.from(detailContent.querySelectorAll('.dw-photo-chk:checked')).map(function(c){ return Number(c.value); });
      if (!code){ A.toast('Select or enter an item first.', true); return; }
      if (!regs.length){ A.toast('Fetch or add at least one register number.', true); return; }
      if (!aids.length){ A.toast('Check at least one stage photo.', true); return; }
      this.disabled = true;
      try {
        for (var i = 0; i < aids.length; i++){
          var res = await A.api('/api/v1/photos/assign-by-register', {
            method: 'POST',
            body: { asset_id: aids[i], venue_id: curBatchVenueId, item_code: code, register_nos: regs }
          });
          if (!res.ok){ A.toast('Assign failed: ' + (res.detail || res.status), true); return; }
        }
        A.toast('Assigned ' + regs.join(', ') + ' to ' + aids.length + ' photo(s).');
        openBatch(curBatchId);
      } finally {
        this.disabled = false;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    view = el('batches-view'); detailView = el('batch-detail-view'); detailContent = el('batch-content');
    liveStrip = el('dw-live-strip'); dwConn = el('dw-conn');

    el('logout-btn').addEventListener('click', window.KalAuth.logout);
    el('refresh-batches-btn').addEventListener('click', function(){ curBatchId ? openBatch(curBatchId) : loadBatches(); });
    el('toggle-live-stages').addEventListener('click', function(){ liveStrip.classList.toggle('hidden'); });

    el('dw-tabs').addEventListener('click', function(ev){
      var t = ev.target.closest('.tab');
      if (!t) return;
      curStatus = t.dataset.status;
      document.querySelectorAll('#dw-tabs .tab').forEach(function(x){ x.classList.toggle('active', x === t); });
      detailView.classList.add('hidden'); view.classList.remove('hidden');
      loadBatches();
    });

    el('back-to-batches').addEventListener('click', function(){
      revokeBlobs(); detailView.classList.add('hidden'); view.classList.remove('hidden'); loadBatches();
    });

    el('dw-publish-top').addEventListener('click', async function(){
      if (!curBatchId) return;
      if (await A.req('/api/v1/photos/batches/' + curBatchId + '/publish', { method: 'POST' }, 'Batch #' + curBatchId + ' published!')){
        detailView.classList.add('hidden'); view.classList.remove('hidden'); loadBatches();
      }
    });

    A.on(view, 'click', '[data-open-batch]', function(b){ openBatch(Number(b.dataset.openBatch)); });

    A.on(detailContent, 'input', '[data-search-asset]', A.debounce(async function(inp){
      var aid = inp.dataset.searchAsset, q = inp.value.trim(), box = el('matches-' + aid);
      if (!q){ box.innerHTML = ''; return; }
      var r = await A.api('/api/v1/photos/participants/search?q=' + encodeURIComponent(q));
      if (!r.ok) return;
      var html = [];
      (r.data.participants || []).forEach(function(p){
        (p.entries || []).forEach(function(e){
          html.push('<button type="button" class="small" style="margin:.2rem .3rem .2rem 0" data-assign-asset="' + aid + '" data-entry-id="' + e.id + '">+ ' + esc(p.register_no) + ' · ' + esc(p.name) + ' (' + esc(e.item_code) + ')</button>');
        });
        html.push('<button type="button" class="small" style="margin:.2rem .3rem .2rem 0" data-team-asset="' + aid + '" data-team-reg="' + esc(p.register_no) + '">++ Team of #' + esc(p.register_no) + ' (' + esc(p.school_name) + ')</button>');
      });
      box.innerHTML = html.join('') || '<span class="muted small">No matching participants.</span>';
    }, 220));

    A.on(detailContent, 'click', '[data-assign-asset]', async function(b){
      var d = await A.req('/api/v1/photos/assign', { method: 'POST', body: { asset_id: Number(b.dataset.assignAsset), participant_entry_ids: [Number(b.dataset.entryId)] } }, 'Assigned.');
      if (d) openBatch(d.batch_id);
    });

    A.on(detailContent, 'click', '[data-team-asset]', async function(b){
      var reg = b.dataset.teamReg;
      var r = await A.api('/api/v1/photos/team-lookup?register_no=' + encodeURIComponent(reg) + (batchItemCode ? '&item_code=' + encodeURIComponent(batchItemCode) : ''));
      if (!r.ok) return;
      (r.data.team || []).forEach(function(m){ addBatchChip(m.register_no, m.name); });
      A.toast('Loaded school team for #' + reg + ' into Quick Assign toolbar.');
    });

    A.on(detailContent, 'click', '[data-dw-rm-chip]', function(b){
      batchTeamRegs.splice(Number(b.dataset.dwRmChip), 1);
      renderBatchChips();
    });

    A.on(detailContent, 'click', '[data-unassign-asset]', async function(b){
      var d = await A.req('/api/v1/photos/assets/' + b.dataset.unassignAsset + '/entries/' + b.dataset.unassignEntry, { method: 'DELETE' }, 'Tag removed.');
      if (d) openBatch(d.batch_id);
    });

    A.on(detailContent, 'click', '[data-del-asset]', async function(b){
      if (!confirm('Permanently delete this photo?')) return;
      var d = await A.req('/api/v1/photos/assets/' + b.dataset.delAsset, { method: 'DELETE' }, 'Photo deleted.');
      if (d) openBatch(d.batch_id);
    });

    // Zoom Lightbox
    var lb = el('dw-lightbox'), lbImg = el('dw-lb-img');
    A.on(detailContent, 'click', 'img[data-zoomable]', function(img){
      lbImg.src = img.src;
      lb.classList.remove('hidden');
    });
    el('dw-lb-close').addEventListener('click', function(){ lb.classList.add('hidden'); });
    lb.addEventListener('click', function(ev){ if (ev.target === lb) lb.classList.add('hidden'); });

    window.KalAuth.init();
  });

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    el('app').classList.remove('hidden');
    el('who').textContent = (info.email || 'staff') + ' · ' + (info.role || 'dataworker');
    loadSchedule();
    startLiveUpdates();
    loadBatches();
  };
})();
