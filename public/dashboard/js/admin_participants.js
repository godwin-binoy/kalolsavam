(function(){
  'use strict';
  var A = window.KalAPI;
  if (!A) return;

  // -------------------------------------------------------------------------
  // Participants Tab
  // -------------------------------------------------------------------------
  var partDialog = document.getElementById('part-edit-dialog');
  var partForm = document.getElementById('part-edit-form');
  
  document.addEventListener('DOMContentLoaded', function() {
    var tabBtn = document.querySelector('[data-tab="participants"]');
    var view = document.getElementById('view');
    if (!tabBtn || !view) return;

    tabBtn.addEventListener('click', function() {
      document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
      tabBtn.classList.add('active');
      loadParticipants();
    });

    // Close dialog
    if (partDialog) {
      partDialog.addEventListener('click', function(e) {
        if (e.target.hasAttribute('data-cancel-part')) partDialog.close();
      });
    }

    // Save Participant
    if (partForm) {
      partForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        var id = document.getElementById('pe-id').value;
        var payload = {
          register_no: document.getElementById('pe-reg').value,
          name: document.getElementById('pe-name').value,
          school_name: document.getElementById('pe-school').value,
          school_code: document.getElementById('pe-scode').value,
          class: Number(document.getElementById('pe-class').value)
        };
        var url = id ? '/api/v1/admin/participants/' + id : '/api/v1/admin/participants';
        var method = id ? 'PUT' : 'POST';
        
        var r = await A.api(url, { method: method, body: payload });
        if (r.ok) {
          A.toast('Participant saved');
          partDialog.close();
          loadParticipants();
        } else {
          A.toast(r.detail || 'Save failed', true);
        }
      });
    }
  });

  window.openPartEditor = async function(id) {
    if (!partDialog) return;
    document.getElementById('pe-id').value = id || '';
    document.getElementById('pe-reg').value = '';
    document.getElementById('pe-name').value = '';
    document.getElementById('pe-school').value = '';
    document.getElementById('pe-scode').value = '';
    document.getElementById('pe-class').value = '';
    document.getElementById('pe-entries-list').innerHTML = '';

    if (id) {
      var r = await A.api('/api/v1/admin/participants/' + id);
      if (r.ok) {
        var p = r.data.participant;
        document.getElementById('pe-reg').value = p.register_no;
        document.getElementById('pe-name').value = p.name;
        document.getElementById('pe-school').value = p.school_name;
        document.getElementById('pe-scode').value = p.school_code;
        document.getElementById('pe-class').value = p.student_class;
        
        var entries = r.data.entries || [];
        if (entries.length) {
          var html = entries.map(function(e) {
            return '<div class="row" style="border-bottom:1px solid var(--border);padding:.5rem 0">' +
              '<span style="flex:1"><b>' + A.esc(e.item_code) + '</b> · ' + A.esc(e.venue_name) + ' · ' + A.esc(e.perf_date) + '</span>' +
              '<button type="button" class="danger small" onclick="deleteEntry('+id+','+e.id+')">Remove</button>' +
            '</div>';
          }).join('');
          document.getElementById('pe-entries-list').innerHTML = html;
        } else {
          document.getElementById('pe-entries-list').innerHTML = '<p class="muted small">No items added yet.</p>';
        }
      }
    }
    partDialog.showModal();
  };

  window.deleteEntry = async function(pid, eid) {
    if (!confirm('Remove this item?')) return;
    var r = await A.api('/api/v1/admin/participants/'+pid+'/entries/'+eid, { method: 'DELETE' });
    if (r.ok) {
      A.toast('Item removed');
      openPartEditor(pid);
    }
  };

  async function loadParticipants() {
    var view = document.getElementById('view');
    view.innerHTML = '<div class="panel"><p class="muted">Loading registry...</p></div>';
    
    var r = await A.api('/api/v1/admin/participants');
    if (!r.ok) {
      view.innerHTML = '<div class="panel"><p class="err">Failed to load participants (' + r.status + ').</p></div>';
      return;
    }
    
    var data = r.data.participants || [];
    var rows = data.map(function(p) {
      return '<tr>' +
        '<td class="mono">' + A.esc(p.register_no) + '</td>' +
        '<td>' + A.esc(p.name) + '</td>' +
        '<td>' + A.esc(p.school_name) + ' <span class="muted small">(' + A.esc(p.school_code) + ')</span></td>' +
        '<td>' + p.student_class + '</td>' +
        '<td><span class="pill">' + p.entry_count + ' items</span></td>' +
        '<td><button class="small" onclick="openPartEditor('+p.id+')">Edit</button></td>' +
      '</tr>';
    }).join('');

    view.innerHTML =
      '<div class="panel">' +
        '<div class="row" style="margin-bottom:1rem">' +
          '<h2>Participants Registry <span class="badge">' + r.data.total + '</span></h2>' +
          '<span class="spacer" style="flex:1"></span>' +
          '<button onclick="document.getElementById(\'csv-upload\').click()">Import CSV</button>' +
          '<button onclick="exportCSV()">Export CSV</button>' +
          '<button class="primary" onclick="openPartEditor()">Add Participant</button>' +
          '<input type="file" id="csv-upload" style="display:none" accept=".csv">' +
        '</div>' +
        '<div style="overflow-x:auto">' +
          '<table class="tbl">' +
            '<thead><tr><th>Reg No</th><th>Name</th><th>School</th><th>Class</th><th>Entries</th><th>Actions</th></tr></thead>' +
            '<tbody>' + (rows || '<tr><td colspan="6" class="muted center">No participants found.</td></tr>') + '</tbody>' +
          '</table>' +
        '</div>' +
      '</div>';

    var up = document.getElementById('csv-upload');
    if (up) {
      up.addEventListener('change', function() {
        var file = up.files[0];
        if (!file) return;
        var fd = new FormData();
        fd.append('file', file);
        fetch(A.url('/api/v1/admin/participants/import'), {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + A.getToken() },
          body: fd
        }).then(function(res){ return res.json(); }).then(function(d) {
          alert('Import complete: ' + d.participants_created + ' created, ' + d.errors.length + ' errors.');
          loadParticipants();
        }).catch(function(){ alert('Upload failed'); });
      });
    }
  }

  window.exportCSV = function() {
    A.downloadBlob('/api/v1/admin/participants/export.csv', 'participants.csv');
  };

  // -------------------------------------------------------------------------
  // Queue Tab Override (since we need registry dropdown instead of text inputs)
  // -------------------------------------------------------------------------
  var queueTabBtn = document.querySelector('[data-tab="queue"]');
  if (queueTabBtn) {
    // Intercept to stop admin.js from rendering the old UI
    queueTabBtn.addEventListener('click', function(e) {
      e.stopImmediatePropagation();
      document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
      queueTabBtn.classList.add('active');
      loadQueueV2();
    }, true);
  }

  async function loadQueueV2() {
    var view = document.getElementById('view');
    view.innerHTML = '<div class="panel"><p class="muted">Loading queue...</p></div>';
    
    var venuesReq = await A.api('/api/v1/admin/venues');
    var queueReq = await A.api('/api/v1/admin/queue');
    if (!venuesReq.ok || !queueReq.ok) {
      view.innerHTML = '<div class="panel"><p class="err">Failed to load queue.</p></div>';
      return;
    }
    
    var venues = venuesReq.data.venues;
    var items = queueReq.data.items;
    
    // Group by venue
    var byVenue = {};
    venues.forEach(function(v) { byVenue[v.id] = { venue: v, items: [] }; });
    items.forEach(function(i) { if (byVenue[i.venue_id]) byVenue[i.venue_id].items.push(i); });
    
    var html = '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(500px,1fr))">';
    Object.values(byVenue).forEach(function(group) {
      var v = group.venue;
      var rows = group.items.map(function(i) {
        return '<tr>' +
          '<td class="mono">' + (i.chest_no ? '<strong>' + A.esc(i.chest_no) + '</strong>' : '—') + '</td>' +
          '<td>' + A.esc(i.event_code) + ' · ' + A.esc(i.event_title) + '</td>' +
          '<td>' + A.esc(i.student_name) + ' <span class="muted small">(' + A.esc(i.roll) + ')</span><br><span class="muted small">' + A.esc(i.school) + '</span></td>' +
          '<td><span class="status ' + A.esc(i.status) + '">' + A.esc(i.status) + '</span></td>' +
        '</tr>';
      }).join('');

      html += '<section class="panel">' +
        '<h2>' + A.esc(v.name) + '</h2>' +
        '<div class="row" style="margin-bottom:1rem">' +
          '<button class="primary" onclick="openQueueAdd(' + v.id + ')">+ Add to ' + A.esc(v.name) + '</button>' +
        '</div>' +
        '<table class="tbl"><thead><tr><th>Chest</th><th>Event</th><th>Participant</th><th>Status</th></tr></thead>' +
        '<tbody>' + (rows || '<tr><td colspan="4" class="muted">Queue empty.</td></tr>') + '</tbody></table>' +
      '</section>';
    });
    html += '</div>';
    view.innerHTML = html;
  }

  window.openQueueAdd = function(venueId) {
    var dlg = document.getElementById('queue-add-dialog');
    if (!dlg) return;
    document.getElementById('qa-venue').value = venueId;
    document.getElementById('qa-entry-id').value = '';
    document.getElementById('qa-search').value = '';
    document.getElementById('qa-results').innerHTML = '<p class="muted small">Type to search...</p>';
    document.getElementById('qa-chest').value = '';
    dlg.showModal();
  };

  // Queue Search logic
  var searchTimeout;
  var qaSearch = document.getElementById('qa-search');
  if (qaSearch) {
    qaSearch.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      var q = this.value.trim();
      if (q.length < 2) return;
      searchTimeout = setTimeout(async function() {
        var r = await A.api('/api/v1/admin/participants?q=' + encodeURIComponent(q));
        if (!r.ok) return;
        var parts = r.data.participants;
        if (!parts.length) {
          document.getElementById('qa-results').innerHTML = '<p class="muted small">No match.</p>';
          return;
        }
        // Fetch entries for the first match (for simplicity in this quick UI)
        // In a real UI, you'd show a list of entries directly.
        var pid = parts[0].id;
        var pr = await A.api('/api/v1/admin/participants/' + pid);
        if (!pr.ok) return;
        var entries = pr.data.entries;
        
        var html = entries.map(function(e) {
          return '<div class="row" style="border-bottom:1px solid var(--border);padding:.4rem 0">' +
            '<span style="flex:1"><b>' + A.esc(parts[0].name) + '</b> (' + A.esc(parts[0].register_no) + ') - ' + A.esc(e.item_code) + '</span>' +
            '<button type="button" class="primary small" onclick="selectEntryForQueue('+e.id+', \''+A.esc(parts[0].name)+'\', \''+A.esc(e.item_code)+'\')">Select</button>' +
          '</div>';
        }).join('');
        document.getElementById('qa-results').innerHTML = html;
      }, 300);
    });
  }

  window.selectEntryForQueue = function(entryId, name, item) {
    document.getElementById('qa-entry-id').value = entryId;
    document.getElementById('qa-results').innerHTML = '<p class="ok small">Selected: ' + A.esc(name) + ' (' + A.esc(item) + ')</p>';
  };

  var qaForm = document.getElementById('queue-add-form');
  if (qaForm) {
    qaForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var vid = Number(document.getElementById('qa-venue').value);
      var eid = Number(document.getElementById('qa-entry-id').value);
      var chest = document.getElementById('qa-chest').value;
      if (!eid) { alert('Select a participant entry first'); return; }
      
      var r = await A.api('/api/v1/admin/queue', {
        method: 'POST',
        body: { venue_id: vid, participant_entry_id: eid, chest_no: chest }
      });
      if (r.ok) {
        A.toast('Added to queue');
        document.getElementById('queue-add-dialog').close();
        loadQueueV2();
      } else {
        A.toast(r.detail || 'Add failed', true);
      }
    });
  }

})();
