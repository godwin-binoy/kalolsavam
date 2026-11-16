(function(){
  'use strict';
  var A = window.KalAPI, esc = A.esc, el = A.el, view, detailView, detailContent, blobUrls = [];

  function revokeBlobs(){ blobUrls.forEach(function(u){ try { URL.revokeObjectURL(u); } catch(e){} }); blobUrls = []; }

  async function loadImageInto(img, apiPath){
    try {
      var res = await A.authorizedFetch(apiPath, { method: 'GET' });
      if (!res.ok) return;
      var u = URL.createObjectURL(await res.blob());
      blobUrls.push(u); img.src = u;
    } catch(e){}
  }

  async function loadBatches(){
    revokeBlobs();
    view.innerHTML = '<div class="panel"><p class="muted">Loading queue…</p></div>';
    var d = await A.req('/api/v1/photos/batches');
    if (!d){ view.innerHTML = '<div class="panel"><p class="err">Failed to load batches.</p></div>'; return; }
    var batches = d.batches || [];
    view.innerHTML = batches.length ? batches.map(function(b){
      return '<div class="panel"><h3>Batch #' + b.id + ' · ' + esc(b.venue_name || ('Stage ' + b.venue_id)) + '</h3>' +
        '<p class="small muted">Files: ' + b.asset_count + (b.perf_date ? ' · ' + esc(b.perf_date) : '') + '</p>' +
        '<button class="primary" data-open-batch="' + b.id + '">Process Batch</button></div>';
    }).join('') : '<div class="panel"><p class="muted">No batches pending.</p></div>';
  }

  async function openBatch(id){
    revokeBlobs();
    view.classList.add('hidden');
    detailView.classList.remove('hidden');
    detailContent.innerHTML = '<div class="panel"><p class="muted">Loading batch #' + id + '…</p></div>';
    var d = await A.req('/api/v1/photos/batches/' + id);
    if (!d){ detailContent.innerHTML = '<div class="panel"><p class="err">Load failed.</p></div>'; return; }
    var assets = d.assets || [], slips = assets.filter(function(a){ return a.kind === 'slip'; }), stages = assets.filter(function(a){ return a.kind === 'stage'; });

    var slipsHtml = slips.length ? slips.map(function(s){
      return '<img data-auth-src="' + esc(s.url) + '" alt="Slip #' + s.id + '" style="max-width:100%;border-radius:6px;margin-bottom:1rem;border:1px solid var(--border)">';
    }).join('') : '<p class="muted small">No slip photos in this batch.</p>';

    var stagesHtml = stages.map(function(s){
      var tags = (s.assigned_details || []).map(function(x){
        return '<span class="pill ok">' + esc(x.register_no) + ' · ' + esc(x.name) + ' (Item ' + esc(x.item_code) + ')</span>';
      }).join(' ');
      return '<div class="panel" style="margin-bottom:1rem">' +
        '<img data-auth-src="' + esc(s.url) + '" alt="Stage #' + s.id + '" style="max-height:320px;border-radius:6px;margin-bottom:.75rem">' +
        (tags ? '<div style="margin-bottom:.6rem">' + tags + '</div>' : '<p class="muted small">Unassigned</p>') +
        '<div class="row"><input type="search" data-search-asset="' + s.id + '" placeholder="Search student reg no or name…" style="flex:1"></div>' +
        '<div id="matches-' + s.id + '" style="margin-top:.5rem"></div></div>';
    }).join('');

    detailContent.innerHTML = '<div class="split" style="align-items:start"><div class="panel"><h2>Slip Photos</h2>' + slipsHtml + '</div>' +
      '<div><h2>Stage Photos (' + stages.length + ')</h2>' + (stagesHtml || '<p class="muted">None.</p>') + '</div></div>' +
      '<div class="row" style="margin-top:1.25rem"><button class="primary success" data-publish-batch="' + id + '">✔ Publish Batch #' + id + '</button></div>';

    detailContent.querySelectorAll('img[data-auth-src]').forEach(function(img){ loadImageInto(img, img.dataset.authSrc); });
  }

  document.addEventListener('DOMContentLoaded', function(){
    view = el('batches-view'); detailView = el('batch-detail-view'); detailContent = el('batch-content');
    el('logout-btn').addEventListener('click', window.KalAuth.logout);
    el('refresh-batches-btn').addEventListener('click', loadBatches);
    el('back-to-batches').addEventListener('click', function(){
      revokeBlobs(); detailView.classList.add('hidden'); view.classList.remove('hidden'); loadBatches();
    });
    A.on(view, 'click', '[data-open-batch]', function(b){ openBatch(Number(b.dataset.openBatch)); });
    A.on(detailContent, 'input', '[data-search-asset]', A.debounce(async function(inp){
      var aid = inp.dataset.searchAsset, q = inp.value.trim(), box = el('matches-' + aid);
      if (q.length < 2){ box.innerHTML = ''; return; }
      var r = await A.api('/api/v1/photos/participants/search?q=' + encodeURIComponent(q));
      if (!r.ok) return;
      var html = [];
      (r.data.participants || []).forEach(function(p){
        (p.entries || []).forEach(function(e){
          html.push('<button type="button" class="small" style="margin:.2rem .3rem .2rem 0" data-assign-asset="' + aid + '" data-entry-id="' + e.id + '">+ ' + esc(p.register_no) + ' · ' + esc(p.name) + ' (Item ' + esc(e.item_code) + ')</button>');
        });
      });
      box.innerHTML = html.join('') || '<span class="muted small">No matching entries.</span>';
    }, 250));
    A.on(detailContent, 'click', '[data-assign-asset]', async function(b){
      var d = await A.req('/api/v1/photos/assign', { method: 'POST', body: { asset_id: Number(b.dataset.assignAsset), participant_entry_ids: [Number(b.dataset.entryId)] } }, 'Assigned.');
      if (d) openBatch(d.batch_id);
    });
    A.on(detailContent, 'click', '[data-publish-batch]', async function(b){
      var bid = Number(b.dataset.publishBatch);
      if (await A.req('/api/v1/photos/batches/' + bid + '/publish', { method: 'POST' }, 'Batch #' + bid + ' published.')){
        detailView.classList.add('hidden'); view.classList.remove('hidden'); loadBatches();
      }
    });
    window.KalAuth.init();
  });

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    el('app').classList.remove('hidden');
    el('who').textContent = (info.email || 'staff') + ' · ' + (info.role || 'dataworker');
    loadBatches();
  };
})();
