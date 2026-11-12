(function(){
  'use strict';
  var KEY = 'kal_lang';

  var DICT = {
    en: {
      "brand.name": "St. Antony's HSS Mala",
      "brand.sub": "Sub-District School Kalolsavam",
      "nav.home": "Home",
      "nav.venues": "Stages",
      "nav.media": "Photos",
      "nav.facilities": "Facilities",
      "nav.transportation": "Transport",
      "nav.developers": "Team",
      "nav.help": "Help / Emergency",
      "nav.help_fast": "Help",
      "footer.title": "Mala Sub-District School Kalolsavam",
      "footer.address": "St. Antony's Higher Secondary School, Mala, Thrissur, Kerala 680732",
      "footer.dev": "Meet the Developers",
      "btn.explore": "Explore Services",
      "btn.live": "Live Stages",
      "hero.badge": "One Kalolsavam, One Platform",
      "hero.title": "Mala Sub-District<br>School Kalolsavam",
      "hero.desc": "Welcome to the official web desk for participants, parents, and teachers. Track real-time stage events, access verified result declarations, and download stage photographs.",
      "sec.services": "Festival Services & Portals",
      "sec.services.desc": "Search literally anything — stage numbers, items, bus routes, toilets, lunch, medical, or results",
      "search.placeholder": "Search anything",
      "card.stages.title": "Stages & Venues",
      "card.stages.sub": "Module 01 · Live Tracker",
      "card.stages.loc": "Location",
      "card.stages.find": "Find by Item",
      "card.stages.live": "Live Updates",
      "card.fac.title": "Facilities",
      "card.fac.sub": "Module 04 · Campus Facilities",
      "card.fac.green": "Green Room",
      "card.fac.toilet": "Toilet",
      "card.fac.all": "See All",
      "card.media.title": "Media & Streaming",
      "card.media.sub": "Module 03 · Official Media",
      "card.media.photos": "Stage Photos",
      "card.media.live": "Live Streaming",
      "card.results.title": "Results",
      "card.results.sub": "Official Government Portal",
      "card.results.check": "Check Official Results",
      "card.results.hint": "Tap to open the government portal",
      "results.title": "Results",
      "results.subtitle": "Official Government Portal",
      "results.check": "Check Official Results",
      "results.hint": "Tap to open the government portal",
      "card.trans.title": "Transportation",
      "card.trans.sub": "Module 06 · Bus & Auto",
      "card.trans.bus": "Bus Timings",
      "card.trans.auto": "Auto Drivers",
      "card.trans.all": "All Travel Options",
      "card.help.title": "Help & Medical",
      "card.help.sub": "Module 05 · Emergency Directory",
      "card.help.firstaid": "First Aid",
      "card.help.convener": "Convener Desk",
      "card.dev.title": "Meet the Developers & Volunteers",
      "card.dev.sub": "Platform Creators & Backstage Crew",
      "card.dev.desc": "Choose an option below to explore the team and backstage crew behind this platform.",
      "card.dev.devbtn": "Meet Developers",
      "card.dev.volbtn": "Meet Volunteers",
      "card.venue.badge": "Event Venue Location",
      "card.venue.title": "St. Antony's Higher Secondary School",
      "card.venue.addr": "Mala, Thrissur District, Kerala — 680732",
      "card.venue.btn": "Open in Google Maps"
    },
    ml: {
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
      "card.stages.sub": "മൊഡ്യൂൾ 01 · ലൈവ് ട്രാക്കർ",
      "card.stages.loc": "സ്ഥലം",
      "card.stages.find": "ഇനം കൊണ്ട് കണ്ടെത്തുക",
      "card.stages.live": "ലൈവ് അപ്ഡേറ്റുകൾ",
      "card.fac.title": "സൗകര്യങ്ങൾ",
      "card.fac.sub": "മൊഡ്യൂൾ 04 · കാമ്പസ് സൗകര്യങ്ങൾ",
      "card.fac.green": "ഗ്രീൻ റൂം",
      "card.fac.toilet": "ടോയ്ലറ്റ്",
      "card.fac.all": "എല്ലാം കാണുക",
      "card.media.title": "മീഡിയയും സ്ട്രീമിംഗും",
      "card.media.sub": "മൊഡ്യൂൾ 03 · ഔദ്യോഗിക മീഡിയ",
      "card.media.photos": "വേദി ഫോട്ടോകൾ",
      "card.media.live": "ലൈവ് സ്ട്രീമിംഗ്",
      "card.results.title": "ഫലങ്ങൾ",
      "card.results.sub": "ഔദ്യോഗിക സർക്കാർ പോർട്ടൽ",
      "card.results.check": "ഔദ്യോഗിക ഫലങ്ങൾ പരിശോധിക്കുക",
      "card.results.hint": "സർക്കാർ പോർട്ടൽ തുറക്കാൻ ടാപ്പ് ചെയ്യുക",
      "results.title": "ഫലങ്ങൾ",
      "results.subtitle": "ഔദ്യോഗിക സർക്കാർ പോർട്ടൽ",
      "results.check": "ഔദ്യോഗിക ഫലങ്ങൾ പരിശോധിക്കുക",
      "results.hint": "സർക്കാർ പോർട്ടൽ തുറക്കാൻ ടാപ്പ് ചെയ്യുക",
      "card.trans.title": "ഗതാഗതം",
      "card.trans.sub": "മൊഡ്യൂൾ 06 · ബസ് & ഓട്ടോ",
      "card.trans.bus": "ബസ് സമയങ്ങൾ",
      "card.trans.auto": "ഓട്ടോ ഡ്രൈവർമാർ",
      "card.trans.all": "എല്ലാ യാത്രാ ഓപ്ഷനുകളും",
      "card.help.title": "സഹായം & മെഡിക്കൽ",
      "card.help.sub": "മൊഡ്യൂൾ 05 · അടിയന്തര ഡയറക്ടറി",
      "card.help.firstaid": "പ്രഥമ ശുശ്രൂഷ",
      "card.help.convener": "കൺവീനർ ഡെസ്ക്",
      "card.dev.title": "ഡെവലപ്പർമാരെയും വോളന്റിയർമാരെയും കാണുക",
      "card.dev.sub": "പ്ലാറ്റ്ഫോം സ്രഷ്ടാക്കളും അണിയറ പ്രവർത്തകരും",
      "card.dev.desc": "ഈ പ്ലാറ്റ്ഫോമിന് പിന്നിലെ ടീമിനെയും വോളന്റിയർമാരെയും അറിയാൻ തിരഞ്ഞെടുക്കുക.",
      "card.dev.devbtn": "ഡെവലപ്പർമാർ",
      "card.dev.volbtn": "വോളന്റിയർമാർ",
      "card.venue.badge": "വേദി സ്ഥലം",
      "card.venue.title": "സെന്റ് ആന്റണീസ് ഹയർ സെക്കൻഡറി സ്കൂൾ",
      "card.venue.addr": "മാള, തൃശ്ശൂർ ജില്ല, കേരളം — 680732",
      "card.venue.btn": "ഗൂഗിൾ മാപ്പിൽ തുറക്കുക"
    }
  };

  var PHRASES = [
    // Hero Section Phrases
    [/^\s*One\s*Kalolsavam,\s*One\s*Platform\s*$/i, "ഒരു കലോത്സവം, ഒരു പ്ലാറ്റ്ഫോം", "One Kalolsavam, One Platform"],
    [/^\s*Mala\s*Sub-District\s*School\s*Kalolsavam\s*$/i, "മാള ഉപജില്ല<br>സ്കൂൾ കലോത്സവം", "Mala Sub-District<br>School Kalolsavam"],
    [/^\s*Welcome\s*to\s*the\s*official\s*web\s*desk/i, "മത്സരാർത്ഥികൾക്കും, രക്ഷിതാക്കൾക്കും, അധ്യാപകർക്കുമുള്ള ഔദ്യോഗിക വെബ് ഡെസ്കിലേക്ക് സ്വാഗതം. തത്സമയ വേദി വിവരങ്ങൾ, ഫലങ്ങൾ, ഫോട്ടോകൾ എന്നിവ ഇവിടെ ലഭ്യമാണ്.", "Welcome to the official web desk for participants, parents, and teachers. Track real-time stage events, access verified result declarations, and download stage photographs."],
    [/^\s*Explore\s*Services\s*$/i, "സേവനങ്ങൾ കാണുക", "Explore Services"],
    [/^\s*Live\s*Stages\s*$/i, "ലൈവ് വേദികൾ", "Live Stages"],

    // Card Header and Action Phrases
    [/^Stages\s*&\s*Venues$/i, "വേദികളും സ്ഥലങ്ങളും", "Stages & Venues"],
    [/^Module\s*01\s*·\s*Live\s*Tracker$/i, "മൊഡ്യൂൾ 01 · ലൈവ് ട്രാക്കർ", "Module 01 · Live Tracker"],
    [/^Facilities$/i, "സൗകര്യങ്ങൾ", "Facilities"],
    [/^Module\s*04\s*·\s*Campus\s*Facilities$/i, "മൊഡ്യൂൾ 04 · കാമ്പസ് സൗകര്യങ്ങൾ", "Module 04 · Campus Facilities"],
    [/^Media\s*&\s*Streaming$/i, "മീഡിയയും സ്ട്രീമിംഗും", "Media & Streaming"],
    [/^Module\s*03\s*·\s*Official\s*Media$/i, "മൊഡ്യൂൾ 03 · ഔദ്യോഗിക മീഡിയ", "Module 03 · Official Media"],
    [/^Results$/i, "ഫലങ്ങൾ", "Results"],
    [/^Official\s*Government\s*Portal$/i, "ഔദ്യോഗിക സർക്കാർ പോർട്ടൽ", "Official Government Portal"],
    [/^Transportation$/i, "ഗതാഗതം", "Transportation"],
    [/^Module\s*06\s*·\s*Bus\s*&\s*Auto$/i, "മൊഡ്യൂൾ 06 · ബസ് & ഓട്ടോ", "Module 06 · Bus & Auto"],
    [/^Help\s*&\s*Medical$/i, "സഹായം & മെഡിക്കൽ", "Help & Medical"],
    [/^Module\s*05\s*·\s*Emergency\s*Directory$/i, "മൊഡ്യൂൾ 05 · അടിയന്തര ഡയറക്ടറി", "Module 05 · Emergency Directory"],
    [/^Check\s*Official\s*Results$/i, "ഔദ്യോഗിക ഫലങ്ങൾ പരിശോധിക്കുക", "Check Official Results"],
    [/^Tap\s*to\s*open\s*the\s*government\s*portal$/i, "സർക്കാർ പോർട്ടൽ തുറക്കാൻ ടാപ്പ് ചെയ്യുക", "Tap to open the government portal"],
    [/^Location$/i, "സ്ഥലം", "Location"],
    [/^Find\s*by\s*Item$/i, "ഇനം കൊണ്ട് കണ്ടെത്തുക", "Find by Item"],
    [/^Live\s*Updates$/i, "ലൈവ് അപ്ഡേറ്റുകൾ", "Live Updates"],
    [/^Green\s*Room$/i, "ഗ്രീൻ റൂം", "Green Room"],
    [/^Toilet$/i, "ടോയ്ലറ്റ്", "Toilet"],
    [/^See\s*All$/i, "എല്ലാം കാണുക", "See All"],
    [/^Stage\s*Photos$/i, "വേദി ഫോട്ടോകൾ", "Stage Photos"],
    [/^Live\s*Streaming$/i, "ലൈവ് സ്ട്രീമിംഗ്", "Live Streaming"],
    [/^Bus\s*Timings$/i, "ബസ് സമയങ്ങൾ", "Bus Timings"],
    [/^Auto\s*Drivers$/i, "ഓട്ടോ ഡ്രൈവർമാർ", "Auto Drivers"],
    [/^All\s*Travel\s*Options$/i, "എല്ലാ യാത്രാ ഓപ്ഷനുകളും", "All Travel Options"],
    [/^First\s*Aid$/i, "പ്രഥമ ശുശ്രൂഷ", "First Aid"],
    [/^Convener\s*Desk$/i, "കൺവീനർ ഡെസ്ക്", "Convener Desk"],
    [/^Meet\s*the\s*Developers\s*&\s*Volunteers$/i, "ഡെവലപ്പർമാരെയും വോളന്റിയർമാരെയും കാണുക", "Meet the Developers & Volunteers"],
    [/^Platform\s*Creators\s*&\s*Backstage\s*Crew$/i, "പ്ലാറ്റ്ഫോം സ്രഷ്ടാക്കളും അണിയറ പ്രവർത്തകരും", "Platform Creators & Backstage Crew"],
    [/^Meet\s*Developers$/i, "ഡെവലപ്പർമാർ", "Meet Developers"],
    [/^Meet\s*Volunteers$/i, "വോളന്റിയർമാർ", "Meet Volunteers"],
    [/^Event\s*Venue\s*Location$/i, "വേദി സ്ഥലം", "Event Venue Location"],
    [/^Open\s*in\s*Google\s*Maps$/i, "ഗൂഗിൾ മാപ്പിൽ തുറക്കുക", "Open in Google Maps"],
    [/^Festival\s*Services\s*&\s*Portals$/i, "കലോത്സവ സേവനങ്ങളും പോർട്ടലുകളും", "Festival Services & Portals"],
    [/^Help$/i, "സഹായം", "Help"],
    [/^Call\s*Now$/i, "വിളിക്കുക", "Call Now"]
  ];

  function getLang(){
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === 'ml' || saved === 'en') return saved;
    } catch(e){}
    return 'en';
  }

  function applyLang(lang){
    var target = (lang === 'ml') ? 'ml' : 'en';
    document.documentElement.setAttribute('data-lang', target);
    document.documentElement.lang = target;
    try { localStorage.setItem(KEY, target); } catch(e){}

    var dict = DICT[target] || DICT.en;

    // 1. Direct Attribute-based replacement
    document.querySelectorAll('[data-i18n]').forEach(function(el){
      var key = el.getAttribute('data-i18n');
      if (dict[key] != null){
        if (dict[key].indexOf('<') >= 0){
          el.innerHTML = dict[key];
        } else {
          el.textContent = dict[key];
        }
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el){
      var key = el.getAttribute('data-i18n-placeholder');
      if (dict[key] != null){
        el.setAttribute('placeholder', dict[key]);
      }
    });

    // 2. Phrase matching fallback across the whole page body
    var scope = document.getElementById('main') || document.body;
    var elements = scope.querySelectorAll('h1, h2, h3, span, a, p, strong, small');
    elements.forEach(function(el){
      // Allow heading elements (even with <br>) and leaf nodes
      var isHeading = el.tagName === 'H1' || el.classList.contains('fest-title') || el.classList.contains('page-title');
      if (el.children.length > 0 && !isHeading) return;

      var txt = (el.textContent || '').trim().replace(/\s+/g, ' ');
      if (!txt) return;

      for (var i = 0; i < PHRASES.length; i++){
        var rule = PHRASES[i];
        var pattern = rule[0];
        var mlText = rule[1];
        var enText = rule[2];

        if (target === 'ml' && pattern.test(txt)){
          if (mlText.indexOf('<') >= 0) el.innerHTML = mlText;
          else el.textContent = mlText;
          break;
        } else if (target === 'en' && (txt === mlText.replace(/<[^>]+>/g, '').trim() || txt === mlText)){
          if (enText.indexOf('<') >= 0) el.innerHTML = enText;
          else el.textContent = enText;
          break;
        }
      }
    });

    // 3. Update Toggle button aria-label and title
    document.querySelectorAll('[data-lang-toggle]').forEach(function(btn){
      btn.setAttribute('aria-label', target === 'ml' ? 'Switch to English' : 'Switch to Malayalam');
      btn.setAttribute('title', target === 'ml' ? 'Switch to English' : 'Switch to Malayalam');
    });

    window.dispatchEvent(new CustomEvent('kal:langchange', { detail: { lang: target } }));
  }

  function toggleLang(){
    var current = getLang();
    var next = (current === 'en') ? 'ml' : 'en';
    applyLang(next);
  }

  window.KalI18n = {
    get: getLang,
    set: applyLang,
    toggle: toggleLang,
    apply: function(){ applyLang(getLang()); },
    dict: DICT
  };

  function init(){
    applyLang(getLang());
    document.addEventListener('click', function(ev){
      var btn = ev.target.closest('[data-lang-toggle]');
      if (btn){
        ev.preventDefault();
        toggleLang();
      }
    });

    if (window.MutationObserver) {
      var observer = new MutationObserver(function(mutations){
        var shouldUpdate = mutations.some(function(m){
          return m.type === 'childList' && m.addedNodes.length > 0;
        });
        if (shouldUpdate && getLang() === 'ml') {
          observer.disconnect();
          applyLang('ml');
          var main = document.getElementById('main');
          if (main) observer.observe(main, { childList: true, subtree: true });
        }
      });
      var mainEl = document.getElementById('main');
      if (mainEl) observer.observe(mainEl, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
