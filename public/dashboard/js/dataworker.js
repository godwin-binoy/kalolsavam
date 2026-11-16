(function(){
  'use strict';
  var A = window.KalAPI;
  var esc = A.esc;
  var view, detailView, detailContent;
  var blobUrls = [];

  function revokeBlobs(){
    blobUrls.forEach(function(u){ try { URL.revokeObjectURL(u); } catch(e){} });
    blobUrls = [];
  }

  async function loadImageInto(imgEl, apiPath){
    try {
      var res = await A.authorizedFetch(apiPath, { method: 'GET' });
      if (!res.ok) return;
      var u = URL.createObjectURL(await res.blob());
      blobUrls.push(u);
      imgEl.src = u;
    } catch(e){}
  }

  async function loadBatches(){
    revokeBlobs();
    view.innerHTML = '<div class="panel"><p class="muted">Loading queue…</p></div>';
    var r = await A.api('/api/v1/photos/batches');
    if (!r.ok){ view.innerHTML = '<div class="panel"><p class="err">Failed to load batches.</p></div>'; return; }
    var batches = r.data.batches || [];
    if (!batches.length){ view.innerHTML = '<div class="panel"><p class="muted">No batches pending.</p></div>'; return; }
    view.innerHTML = batches.map(function(b){
      return '<div class="panel">' +
        '<h3>Batch #' + b.id + ' · ' + esc(b.venue_name || ('Stage ' + b.venue_id)) + '</h3>' +
        '<p class="small muted">Queue #' + b.queue_item_id + ' · ' + b.asset_count + ' file(s)' +
          (b.perf_date ? ' · ' + esc(b.perf_date) : '') + '</p>' +
        '<button class="primary" data-open-batch="' + b.id + '">Process Batch</button></div>';
    }).join('');
  }

  async function openBatch(id){
    revokeBlobs();
    view.classList.add('hidden');
    detailView.classList.remove('hidden');
    detailContent.innerHTML = '<div class="panel"><p class="muted">Loading batch #' + id + '…</p></div>';

    var r = await A.api('/api/v1/photos/batches/' + id);
    if (!r.ok){ detailContent.innerHTML = '<div class="panel"><p class="err">Load failed.</p></div>'; return; }
    var assets = r.data.assets || [];
    var slips = assets.filter(function(a){ return a.kind === 'slip'; });
    var stages = assets.filter(function(a){ return a.kind === 'stage'; });

    var slipsHtml = slips.length ? slips.map(function(s){
      return '<img data-auth-src="' + esc(s.url) + '" alt="Slip #' + s.id + '" style="max-width:100%;border-radius:6px;margin-bottom:1rem;border:1px solid var(--border)">';
    }).join('') : '<p class="muted small">No slip photos in this batch.</p>';

    var stagesHtml = stages.map(function(s){
      var tags = (s.assigned_details || []).map(function(d){
        return '<span class="pill ok">' + esc(d.register_no) + ' · ' + esc(d.name) + ' (Item ' + esc(d.item_code) + ')</span>';
      }).join(' ');
      return '<div class="panel" style="margin-bottom:1rem" data-asset-box="' + s.id + '">' +
        '<img data-auth-src="' + esc(s.url) + '" alt="Stage #' + s.id + '" style="max-height:320px;border-radius:6px;margin-bottom:.75rem">' +
        (tags ? '<div style="margin-bottom:.6rem">' + tags + '</div>' : '<p class="muted small">Unassigned</p>') +
        '<div class="row"><input type="search" data-search-asset="' + s.id + '" placeholder="Search student reg no or name…" style="flex:1"></div>' +
        '<div id="matches-' + s.id + '" style="margin-top:.5rem"></div>' +
      '</div>';
    }).join('');

    detailContent.innerHTML =
      '<div class="split" style="align-items:start">' +
        '<div class="panel"><h2>Slip Photos</h2>' + slipsHtml + '</div>' +
        '<div><h2>Stage Photos (' + stages.length + ')</h2>' + (stagesHtml || '<p class="muted">None.</p>') + '</div>' +
      '</div>' +
      '<div class="row" style="margin-top:1.25rem">' +
        '<button class="primary success" data-publish-batch="' + id + '">✔ Publish Batch #' + id + '</button>' +
      '</div>';

    detailContent.querySelectorAll('img[data-auth-src]').forEach(function(img){
      loadImageInto(img, img.dataset.authSrc);
    });
  }

  var searchTimers = {};
  document.addEventListener('DOMContentLoaded', function(){
    view = document.getElementById('batches-view');
    detailView = document.getElementById('batch-detail-view');
    detailContent = document.getElementById('batch-content');

    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    document.getElementById('refresh-batches-btn').addEventListener('click', loadBatches);
    document.getElementById('back-to-batches').addEventListener('click', function(){
      revokeBlobs();
      detailView.classList.add('hidden');
      view.classList.remove('hidden');
      loadBatches();
    });

    view.addEventListener('click', function(ev){
      var b = ev.target.closest('[data-open-batch]');
      if (b) openBatch(Number(b.dataset.openBatch));
    });

    detailContent.addEventListener('input', function(ev){
      var inp = ev.target.closest('[data-search-asset]');
      if (!inp) return;
      var aid = inp.dataset.searchAsset;
      var q = inp.value.trim();
      var box = document.getElementById('matches-' + aid);
      clearTimeout(searchTimers[aid]);
      if (q.length < 2){ box.innerHTML = ''; return; }
      searchTimers[aid] = setTimeout(async function(){
        var r = await A.api('/api/v1/photos/participants/search?q=' + encodeURIComponent(q));
        if (!r.ok) return;
        var html = [];
        (r.data.participants || []).forEach(function(p){
          (p.entries || []).forEach(function(e){
            html.push(
              '<button type="button" class="small" style="margin:.2rem .3rem .2rem 0" ' +
              'data-assign-asset="' + aid + '" data-entry-id="' + e.id + '">' +
              '+ ' + esc(p.register_no) + ' · ' + esc(p.name) + ' (Item ' + esc(e.item_code) + ')</button>'
            );
          });
        });
        box.innerHTML = html.join('') || '<span class="muted small">No matching entries.</span>';
      }, 260);
    });

    detailContent.addEventListener('click', async function(ev){
      var assignBtn = ev.target.closest('[data-assign-asset]');
      if (assignBtn){
        var aid = Number(assignBtn.dataset.assignAsset);
        var eid = Number(assignBtn.dataset.entryId);
        var r = await A.api('/api/v1/photos/assign', { method: 'POST', body: { asset_id: aid, participant_entry_ids: [eid] } });
        if (r.ok){ A.toast('Assigned.'); openBatch(r.data.batch_id); }
        else A.toast('Assign failed: ' + (r.detail || r.status), true);
        return;
      }
      var pubBtn = ev.target.closest('[data-publish-batch]');
      if (pubBtn){
        var bid = Number(pubBtn.dataset.publishBatch);
        var pr = await A.api('/api/v1/photos/batches/' + bid + '/publish', { method: 'POST' });
        if (pr.ok){
          A.toast('Batch #' + bid + ' published.');
          detailView.classList.add('hidden');
          view.classList.remove('hidden');
          loadBatches();
        } else A.toast('Publish failed: ' + (pr.detail || pr.status), true);
      }
    });

    window.KalAuth.init();
  });

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent = (info.email || info.username || 'staff') + ' · ' + (info.role || 'dataworker');
    loadBatches();
  };
})();
