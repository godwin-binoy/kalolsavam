(function(){
  'use strict';
  var A = window.KalAPI;
  if (!A) return;

  document.addEventListener('DOMContentLoaded', function() {
    var tabBtn = document.querySelector('[data-tab="participants"]');
    var view = document.getElementById('view');
    if (!tabBtn || !view) return;

    tabBtn.addEventListener('click', function() {
      document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
      tabBtn.classList.add('active');
      loadParticipants();
    });

    function loadParticipants() {
      view.innerHTML = '<div class="panel"><p class="muted">Loading registry...</p></div>';
      
      A.api('/api/v1/admin/participants').then(function(r) {
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
            '<td><button class="small danger" onclick="alert(\'Edit interface coming next block!\')">Edit</button></td>' +
          '</tr>';
        }).join('');

        view.innerHTML =
          '<div class="panel">' +
            '<div class="row" style="margin-bottom:1rem">' +
              '<h2>Participants Registry <span class="badge">' + r.data.total + '</span></h2>' +
              '<span class="spacer" style="flex:1"></span>' +
              '<input type="file" id="csv-upload" style="display:none" accept=".csv">' +
              '<button class="primary" onclick="document.getElementById(\'csv-upload\').click()">Upload CSV</button>' +
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
            
            // Need direct fetch since A.api strips FormData headers
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
      });
    }
  });
})();
