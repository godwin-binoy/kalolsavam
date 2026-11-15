(function(){
  'use strict';
  var A = window.KalAPI;
  var view = document.getElementById('batches-view');
  var detailView = document.getElementById('batch-detail-view');
  var detailContent = document.getElementById('batch-content');

  window.onKalLogin = function(info){
    document.body.classList.remove('login-body');
    document.querySelector('.login-card').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('who').textContent = (info.email || info.username || 'staff');
    loadBatches();
  };

  document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('logout-btn').addEventListener('click', window.KalAuth.logout);
    window.KalAuth.init();
  });

  async function loadBatches() {
    view.innerHTML = '<p class="muted">Loading queue...</p>';
    var r = await A.api('/api/v1/photos/batches');
    if (!r.ok) { view.innerHTML = '<p class="err">Failed to load.</p>'; return; }
    
    var batches = r.data.batches;
    if (!batches.length) {
      view.innerHTML = '<p class="muted">No batches pending.</p>';
      return;
    }
    
    var html = batches.map(function(b) {
      return '<div class="panel">' +
        '<h3>Batch #' + b.id + '</h3>' +
        '<p class="small">Item: ' + b.queue_item_id + ' | ' + b.perf_date + '</p>' +
        '<button class="primary" onclick="openBatch('+b.id+')">Process Batch</button>' +
      '</div>';
    }).join('');
    view.innerHTML = html;
  }

  window.openBatch = async function(id) {
    view.classList.add('hidden');
    detailView.classList.remove('hidden');
    detailContent.innerHTML = '<p>Loading...</p>';
    
    var r = await A.api('/api/v1/photos/batches/' + id);
    if (!r.ok) { detailContent.innerHTML = '<p class="err">Load failed</p>'; return; }
    
    var assets = r.data.assets;
    var slips = assets.filter(a => a.kind === 'slip');
    var stages = assets.filter(a => a.kind === 'stage');
    
    var html = '<div class="row" style="align-items:flex-start;gap:2rem">';
    
    // Slips column
    html += '<div style="flex:1"><h3>Slips</h3>';
    slips.forEach(s => { html += '<img src="' + A.url(s.url) + '" style="max-width:100%;border-radius:4px;margin-bottom:1rem">'; });
    html += '</div>';
    
    // Stages column
    html += '<div style="flex:2"><h3>Stage Photos</h3>';
    stages.forEach(s => {
      var assigned = s.assigned_to.length > 0;
      html += '<div class="panel" style="margin-bottom:1rem">';
      html += '<img src="' + A.url(s.url) + '" style="max-height:300px;border-radius:4px">';
      if (assigned) {
        html += '<p class="ok small">Assigned to Entry ID: ' + s.assigned_to.join(', ') + '</p>';
      } else {
        html += '<div class="row"><input type="text" id="assign-'+s.id+'" placeholder="Entry ID(s) comma separated" style="flex:1">' +
                '<button onclick="assignAsset('+s.id+')">Assign</button></div>';
      }
      html += '</div>';
    });
    html += '</div></div>';
    
    html += '<div class="row" style="margin-top:2rem"><button class="primary success" onclick="publishBatch('+id+')">Publish All</button></div>';
    detailContent.innerHTML = html;
  };

  window.assignAsset = async function(assetId) {
    var inp = document.getElementById('assign-' + assetId).value;
    var ids = inp.split(',').map(x => parseInt(x.trim())).filter(x => !isNaN(x));
    if (!ids.length) return;
    var r = await A.api('/api/v1/photos/assign', { method: 'POST', body: { asset_id: assetId, participant_entry_ids: ids } });
    if (r.ok) { A.toast('Assigned'); openBatch(r.data.batch_id || document.querySelector('.panel h3').textContent.split('#')[1]); }
  };

  window.publishBatch = async function(id) {
    var r = await A.api('/api/v1/photos/batches/'+id+'/publish', { method: 'POST' });
    if (r.ok) { A.toast('Published'); detailView.classList.add('hidden'); view.classList.remove('hidden'); loadBatches(); }
  };
})();
