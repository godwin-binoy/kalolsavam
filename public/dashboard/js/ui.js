(function(){
  'use strict';
  var A = window.KalAPI;

  function initPasswordModal(){
    var dlg = document.getElementById('self-password-dialog');
    if (!dlg) return;
    var form = document.getElementById('self-password-form');
    var openBtn = document.getElementById('change-pass-btn');

    if (openBtn) {
      openBtn.addEventListener('click', function(){ dlg.showModal(); });
    }

    form.addEventListener('submit', async function(ev){
      ev.preventDefault();
      var oldP = document.getElementById('self-old-pass').value;
      var newP = document.getElementById('self-new-pass').value;
      var r = await window.KalAuth.changePassword(oldP, newP);
      if (r.ok){
        A.toast('Password changed successfully.');
        form.reset();
        dlg.close();
      } else {
        A.toast('Password change failed: ' + (r.detail || r.status), true);
      }
    });

    dlg.addEventListener('click', function(ev){
      if (ev.target.hasAttribute('data-cancel-self-pass') || ev.target === dlg){
        dlg.close();
      }
    });
  }

  function setupExportInterceptors(){
    document.addEventListener('click', function(ev){
      var a = ev.target.closest('a[href*="/export/"], button[data-export]');
      if (!a) return;
      var href = a.getAttribute('href') || a.getAttribute('data-export');
      if (href && href.indexOf('/export/') >= 0){
        ev.preventDefault();
        var fname = href.split('/').pop().split('?')[0] || 'export.csv';
        A.downloadBlob(href, fname);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    initPasswordModal();
    setupExportInterceptors();
  });

  window.KalUI = {
    initPasswordModal: initPasswordModal,
    setupExportInterceptors: setupExportInterceptors
  };
})();
