(function(){
  'use strict';
  var html=document.documentElement;
  var KEY='kal_theme';
  function isDark(){return html.classList.contains('dark')}
  function sync(){
    var btn=document.getElementById('theme');
    if(btn) btn.textContent=isDark()?'☀':'☾';
  }
  function toggle(){
    var d=html.classList.toggle('dark');
    try{localStorage.setItem(KEY,d?'dark':'light')}catch(e){}
    sync();
  }
  function initTheme(){
    sync();
    var btn=document.getElementById('theme');
    if(btn) btn.addEventListener('click',toggle);
  }
  function initMenu(){
    var btn=document.getElementById('menu');
    var nav=document.getElementById('mnav');
    if(!btn||!nav) return;
    btn.addEventListener('click',function(){
      var open=nav.hasAttribute('hidden');
      if(open){nav.removeAttribute('hidden');btn.setAttribute('aria-expanded','true')}
      else{nav.setAttribute('hidden','');btn.setAttribute('aria-expanded','false')}
    });
  }
  function init(){
    initTheme();
    initMenu();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
