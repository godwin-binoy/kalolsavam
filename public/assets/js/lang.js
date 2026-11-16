(function(){
  'use strict';
  var KEY = 'kal_lang';

  var ML = {
    "banner.dev": "ഈ വെബ്സൈറ്റ് സജീവ നിർമ്മാണ ഘട്ടത്തിലാണ് — വിവരങ്ങളും സൗകര്യങ്ങളും അപ്ഡേറ്റ് ചെയ്തുകൊണ്ടിരിക്കുന്നു.",
    "brand.name": "സെന്റ് ആന്റണീസ് HSS മാള",
    "brand.sub": "ഉപജില്ല സ്കൂൾ കലോത്സവം",
    "nav.home": "ഹോം",
    "nav.venues": "വേദികൾ",
    "nav.media": "ഫോട്ടോകൾ",
    "nav.facilities": "സൗകര്യങ്ങൾ",
    "nav.transportation": "ഗതാഗതം",
    "nav.developers": "ടീം",
    "nav.help": "സഹായം / അടിയന്തരം",
    "nav.help_fast": "സഹായം",
    "footer.title": "മാള ഉപജില്ല സ്കൂൾ കലോത്സവം",
    "footer.address": "സെന്റ് ആന്റണീസ് ഹയർ സെക്കൻഡറി സ്കൂൾ, മാള, തൃശ്ശൂർ, കേരളം 680732",
    "footer.dev": "ഡെവലപ്പർമാരെ കാണുക",
    "btn.explore": "സേവനങ്ങൾ കാണുക",
    "btn.live": "ലൈവ് വേദികൾ",
    "hero.badge": "ഒരു കലോത്സവം, ഒരു പ്ലാറ്റ്ഫോം",
    "hero.title": "മാള ഉപജില്ല<br>സ്കൂൾ കലോത്സവം",
    "hero.desc": "മത്സരാർത്ഥികൾക്കും, രക്ഷിതാക്കൾക്കും, അധ്യാപകർക്കുമുള്ള ഔദ്യോഗിക വെബ് ഡെസ്കിലേക്ക് സ്വാഗതം. തത്സമയ വേദി വിവരങ്ങൾ, ഫലങ്ങൾ, ഫോട്ടോകൾ എന്നിവ ഇവിടെ ലഭ്യമാണ്.",
    "sec.services": "കലോത്സവ സേവനങ്ങളും പോർട്ടലുകളും",
    "sec.services.desc": "എന്തും തിരയുക — വേദി നമ്പറുകൾ, ഇനങ്ങൾ, ബസ് റൂട്ടുകൾ, ടോയ്ലറ്റുകൾ, ഊണ്, മെഡിക്കൽ, ഫലങ്ങൾ",
    "search.placeholder": "എന്തും തിരയുക",
    "card.stages.title": "വേദികളും സ്ഥലങ്ങളും",
    "card.stages.sub": "ലൈവ് ട്രാക്കർ",
    "card.stages.loc": "സ്ഥലം",
    "card.stages.find": "ഇനം കൊണ്ട് കണ്ടെത്തുക",
    "card.stages.live": "ലൈവ് അപ്ഡേറ്റുകൾ",
    "card.fac.title": "സൗകര്യങ്ങൾ",
    "card.fac.sub": "കാമ്പസ് സൗകര്യങ്ങൾ",
    "card.fac.green": "ഗ്രീൻ റൂം",
    "card.fac.toilet": "ടോയ്ലറ്റ്",
    "card.fac.all": "എല്ലാം കാണുക",
    "card.media.title": "മീഡിയയും സ്ട്രീമിംഗും",
    "card.media.sub": "ഔദ്യോഗിക മീഡിയ",
    "card.media.photos": "വേദി ഫോട്ടോകൾ",
    "card.media.live": "ലൈവ് സ്ട്രീമിംഗ്",
    "card.results.title": "ഫലങ്ങൾ",
    "card.results.sub": "ഔദ്യോഗിക സർക്കാർ പോർട്ടൽ",
    "card.results.check": "ഔദ്യോഗിക ഫലങ്ങൾ പരിശോധിക്കുക",
    "card.results.hint": "സർക്കാർ പോർട്ടൽ തുറക്കാൻ ടാപ്പ് ചെയ്യുക",
    "card.trans.title": "ഗതാഗതം",
    "card.trans.sub": "ബസ് & ഓട്ടോ",
    "card.trans.bus": "ബസ് സമയങ്ങൾ",
    "card.trans.auto": "ഓട്ടോ ഡ്രൈവർമാർ",
    "card.help.title": "സഹായം & മെഡിക്കൽ",
    "card.help.sub": "അടിയന്തര ഡയറക്ടറി",
    "card.help.firstaid": "പ്രഥമ ശുശ്രൂഷ",
    "card.help.convener": "കൺവീനർ ഡെസ്ക്",
    "card.dev.title": "ഞങ്ങളുടെ ടീമിനെ കാണുക",
    "card.dev.sub": "പ്ലാറ്റ്ഫോം സ്രഷ്ടാക്കളും അണിയറ പ്രവർത്തകരും",
    "card.dev.desc": "ഈ പ്ലാറ്റ്ഫോമിന് പിന്നിലെ ടീമിനെയും വോളന്റിയർമാരെയും അറിയാൻ തിരഞ്ഞെടുക്കുക.",
    "card.dev.devbtn": "ഡെവലപ്പർമാർ",
    "card.dev.volbtn": "വോളന്റിയർമാർ",
    "card.venue.badge": "വേദി സ്ഥലം",
    "card.venue.title": "സെന്റ് ആന്റണീസ് ഹയർ സെക്കൻഡറി സ്കൂൾ",
    "card.venue.addr": "മാള, തൃശ്ശൂർ ജില്ല, കേരളം — 680732",
    "card.venue.btn": "ഗൂഗിൾ മാപ്പിൽ തുറക്കുക"
  };

  var PHRASE_ML = {
    "stages & venues": "വേദികളും സ്ഥലങ്ങളും", "facilities": "സൗകര്യങ്ങൾ", "transportation": "ഗതാഗതം",
    "location": "സ്ഥലം", "find by item": "ഇനം കൊണ്ട് കണ്ടെത്തുക", "live updates": "ലൈവ് അപ്ഡേറ്റുകൾ",
    "green room": "ഗ്രീൻ റൂം", "toilet": "ടോയ്ലറ്റ്", "see all": "എല്ലാം കാണുക",
    "stage photos": "വേദി ഫോട്ടോകൾ", "live streaming": "ലൈവ് സ്ട്രീമിംഗ്", "bus timings": "ബസ് സമയങ്ങൾ",
    "auto drivers": "ഓട്ടോ ഡ്രൈവർമാർ", "first aid": "പ്രഥമ ശുശ്രൂഷ", "convener desk": "കൺവീനർ ഡെസ്ക്",
    "help": "സഹായം", "call now": "വിളിക്കുക"
  };

  function getLang(){
    try { if (localStorage.getItem(KEY) === 'ml') return 'ml'; } catch(e){}
    return 'en';
  }

  function applyLang(lang){
    var target = lang === 'ml' ? 'ml' : 'en';
    document.documentElement.setAttribute('data-lang', target);
    document.documentElement.lang = target;
    try { localStorage.setItem(KEY, target); } catch(e){}

    document.querySelectorAll('[data-i18n]').forEach(function(el){
      if (el._kalEn == null) el._kalEn = el.innerHTML;
      var v = target === 'ml' ? ML[el.getAttribute('data-i18n')] : el._kalEn;
      if (v != null){ if (v.indexOf('<') >= 0) el.innerHTML = v; else el.textContent = v; }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el){
      if (el._kalEnPh == null) el._kalEnPh = el.getAttribute('placeholder') || '';
      var v = target === 'ml' ? ML[el.getAttribute('data-i18n-placeholder')] : el._kalEnPh;
      if (v != null) el.setAttribute('placeholder', v);
    });

    var scope = document.getElementById('main') || document.body;
    scope.querySelectorAll('h1, h2, h3, span, a, p, strong, small').forEach(function(el){
      if (el.hasAttribute('data-i18n') || el.children.length > 0) return;
      if (el._kalEnTxt == null) el._kalEnTxt = el.textContent;
      if (target === 'en'){ el.textContent = el._kalEnTxt; return; }
      var key = (el._kalEnTxt || '').trim().replace(/\s+/g, ' ').toLowerCase();
      if (PHRASE_ML[key]) el.textContent = PHRASE_ML[key];
    });

    document.querySelectorAll('[data-lang-toggle]').forEach(function(btn){
      var lbl = target === 'ml' ? 'Switch to English' : 'Switch to Malayalam';
      btn.setAttribute('aria-label', lbl);
      btn.setAttribute('title', lbl);
    });
  }

  window.KalI18n = {
    get: getLang,
    set: applyLang,
    toggle: function(){ applyLang(getLang() === 'en' ? 'ml' : 'en'); },
    apply: function(){ applyLang(getLang()); }
  };

  function init(){
    if (getLang() === 'ml') applyLang('ml');
    document.addEventListener('click', function(ev){
      if (ev.target.closest('[data-lang-toggle]')){ ev.preventDefault(); window.KalI18n.toggle(); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
