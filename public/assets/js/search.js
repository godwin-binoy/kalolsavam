/* Universal site-wide advanced search with phonetic & transliteration normalization. */
(function () {
  'use strict';

  var SYNONYMS = {
    'kavyakeali': 'kavyakeli kavya keli',
    'kavyakeli': 'kavyakeali kavya keli',
    'aksharashlokam': 'aksharaslokam akshara slokam',
    'aksharaslokam': 'aksharashlokam akshara slokam',
    'padhyam': 'padyam kavitha kavithaparayanam recitation chollal poem',
    'padyam': 'padhyam kavitha kavithaparayanam recitation chollal poem',
    'chollal': 'cholal padyam padhyam kavitha recitation',
    'cholal': 'chollal padyam padhyam kavitha recitation',
    'kavitha': 'kavithaparayanam padyam padhyam recitation poem chollal',
    'kavithaparayanam': 'kavitha padyam padhyam recitation poem chollal',
    'recitation': 'padyam padhyam kavitha kavithaparayanam chollal poem',
    'poem': 'padyam padhyam kavitha kavithaparayanam recitation',
    'hss': 'hss higher secondary plus two plus one',
    'hs': 'hs high school',
    'up': 'up upper primary',
    'lp': 'lp lower primary',
    'gaanaalapanam': 'ganalapanam sangeetham song',
    'ganalapanam': 'gaanaalapanam sangeetham song',
    'shasthriya': 'shastriya sasthriya classical sangeetham',
    'shastriya': 'shasthriya sasthriya classical sangeetham',
    'sasthriya': 'shasthriya shastriya classical sangeetham',
    'classical': 'shasthriya shastriya sasthriya sangeetham music',
    'sangeetham': 'music song classical shasthriya',
    'music': 'sangeetham classical shasthriya',
    'dance': 'nritham natyam bharathanatyam nadodi kuchuppudi mohiniyattam keralanadanam',
    'kuchipudi': 'kuchuppudi dance',
    'kuchuppudi': 'kuchipudi dance',
    'dafmuttu': 'duffmuttu',
    'duffmuttu': 'dafmuttu',
    'vattapattu': 'vattappattu',
    'vattappattu': 'vattapattu',
    'thiruvathira': 'thiruvathirakkali',
    'thiruvathirakkali': 'thiruvathira',
    'drama': 'nadakam',
    'nadakam': 'drama play',
    'mime': 'mookabhinayam',
    'mookabhinayam': 'mime',
    'monoact': 'mono act',
    'drawing': 'chithra pencil',
    'painting': 'colouring oil',
    'watercolor': 'water colouring',
    'toilet': 'washroom bathroom wc restroom',
    'bathroom': 'toilet washroom',
    'food': 'dining oottupura lunch meals',
    'lunch': 'dining oottupura meals',
    'doctor': 'medical firstaid ambulance',
    'ambulance': 'medical',
    'result': 'results',
    'results': 'result scores marks kite ulsavam',
    'bus': 'ksrtc travel stand',
    'ksrtc': 'bus',
    'auto': 'autorickshaw driver taxi',
    'rickshaw': 'auto',
    'photo': 'photos pictures gallery',
    'photos': 'photo pictures gallery'
  };

  function norm(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/padhyam/g, 'padyam')
      .replace(/kavya\s*k[ea]+li/g, 'kavyakeli')
      .replace(/akshara\s*sh?lokam/g, 'aksharaslokam')
      .replace(/kavitha\s*parayanam/g, 'kavithaparayanam')
      .replace(/gaana+lapanam/g, 'ganalapanam')
      .replace(/shastriya|sasthriya/g, 'shasthriya')
      .replace(/kuchipudi/g, 'kuchuppudi')
      .replace(/duff?mutt[u]?|dafmutt[u]?/g, 'duffmuttu')
      .replace(/parichamutt[u]?(\s*kali)?/g, 'parichamuttukali')
      .replace(/poora+k+ali/g, 'poorakkali')
      .replace(/ma+rgam\s*kali/g, 'margamkali')
      .replace(/lalitha\s*ga+nam/g, 'lalithagaanam')
      .replace(/sangha\s*ga+nam/g, 'sanghagaanam')
      .replace(/deshabhakthi\s*ga+nam/g, 'deshabhakthigaanam')
      .replace(/ma+ppila\s*pa+ttu/g, 'mappilappattu')
      .replace(/vattap+a+ttu/g, 'vattappattu')
      .replace(/na+dan\s*pa+ttu/g, 'nadan pattu')
      .replace(/[\s\-_.:·,()]+/g, ' ')
      .trim();
  }

  function compact(s) {
    return String(s || '').toLowerCase().replace(/[^a-z0-9\u0d00-\u0d7f]/g, '');
  }

  function isSubseq(q, target) {
    if (q.length < 3 || q.length > target.length) return false;
    var i = 0, j = 0;
    while (i < q.length && j < target.length) {
      if (q[i] === target[j]) i++;
      j++;
    }
    return i === q.length;
  }

  function esc(s) {
    return window.Kal ? window.Kal.esc(s) : String(s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function getBase() {
    var b = (document.body && document.body.getAttribute('data-base')) || '/';
    return b.endsWith('/') ? b : b + '/';
  }

  function resolveHref(h) {
    if (!h) return getBase();
    if (/^(?:https?:|tel:|mailto:)/i.test(h)) return h;
    return getBase() + String(h).replace(/^\/+/, '');
  }

  function searchItems(rawQuery, maxResults) {
    var data = window.KAL_SEARCH_INDEX || [];
    var q = norm(rawQuery);
    if (!q) return [];

    var tokens = q.split(' ').filter(Boolean);
    var rawTokens = rawQuery.toLowerCase().split(/[\s\-_.:·,()]+/).filter(Boolean);
    var qComp = compact(rawQuery);
    var scored = [];

    for (var i = 0; i < data.length; i++) {
      var it = data[i];
      var tNorm = norm(it.t);
      var cNorm = norm(it.c);
      var dNorm = norm(it.d);
      var kNorm = norm(it.k);
      var hayNorm = tNorm + ' ' + cNorm + ' ' + dNorm + ' ' + kNorm;

      var tRaw = (it.t || '').toLowerCase();
      var hayRaw = tRaw + ' ' + (it.c || '').toLowerCase() + ' ' + (it.d || '').toLowerCase() + ' ' + (it.k || '').toLowerCase();
      var hayComp = compact(hayRaw);

      var allMatch = true;
      var score = 0;

      for (var ti = 0; ti < tokens.length; ti++) {
        var tk = tokens[ti];
        var rawTk = rawTokens[ti] || tk;
        var altList = (SYNONYMS[tk] ? SYNONYMS[tk].split(' ') : [])
          .concat(SYNONYMS[rawTk] ? SYNONYMS[rawTk].split(' ') : []);
        var matchedTok = false;

        if (tNorm.indexOf(tk) === 0 || tRaw.indexOf(rawTk) === 0) { score += 95; matchedTok = true; }
        else if (tNorm.indexOf(tk) >= 0 || tRaw.indexOf(rawTk) >= 0) { score += 50; matchedTok = true; }
        else if (cNorm.indexOf(tk) >= 0) { score += 35; matchedTok = true; }
        else if (dNorm.indexOf(tk) >= 0) { score += 20; matchedTok = true; }
        else if (kNorm.indexOf(tk) >= 0 || hayNorm.indexOf(tk) >= 0) { score += 15; matchedTok = true; }
        else if (hayComp.indexOf(compact(tk)) >= 0 || hayComp.indexOf(compact(rawTk)) >= 0) { score += 12; matchedTok = true; }
        else if (altList.some(function (a) { return hayNorm.indexOf(a) >= 0 || hayRaw.indexOf(a) >= 0; })) { score += 12; matchedTok = true; }

        if (!matchedTok) { allMatch = false; break; }
      }

      if (!allMatch && qComp.length >= 4 && isSubseq(qComp, compact(tRaw))) {
        score = 8;
        allMatch = true;
      }

      if (allMatch) {
        if (it.g === 'venues' && /\b(stage|venue|room)\b/i.test(rawQuery)) score += 15;
        scored.push({ item: it, score: score });
      }
    }

    scored.sort(function (a, b) {
      return b.score - a.score || a.item.t.length - b.item.t.length;
    });

    return scored.slice(0, maxResults || 14).map(function (s) { return s.item; });
  }

  function renderRows(items, activeIdx) {
    if (!items.length) {
      return '<div class="search-empty">No matches found. Try stage number, item name, bus stop, auto driver, facility, or phone number.</div>';
    }
    return items.map(function (m, idx) {
      var href = resolveHref(m.h);
      var ext = /^https?:/i.test(href) ? ' target="_blank" rel="noopener"' : '';
      return '<a href="' + esc(href) + '"' + ext + ' class="search-result-item' + (idx === activeIdx ? ' selected' : '') + '" data-idx="' + idx + '">' +
        '<div style="min-width:0;flex:1">' +
          '<div style="display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;margin-bottom:.18rem">' +
            '<span class="search-cat-pill">' + esc(m.c) + '</span>' +
            '<strong style="font-size:.94rem;color:var(--text-heading)">' + esc(m.t) + '</strong>' +
          '</div>' +
          '<div style="font-size:.8rem;color:var(--muted);line-height:1.35">' + esc(m.d) + '</div>' +
        '</div>' +
        '<span style="font-size:1.05rem;color:var(--subtle);flex-shrink:0">&rarr;</span>' +
      '</a>';
    }).join('');
  }

  function bindSearchBar(input, dropdown) {
    if (!input || !dropdown) return;
    var curItems = [], activeIdx = -1;

    function update() {
      var val = input.value.trim();
      if (!val) {
        dropdown.classList.add('hidden');
        dropdown.innerHTML = '';
        curItems = [];
        activeIdx = -1;
        return;
      }
      curItems = searchItems(val, 14);
      activeIdx = curItems.length ? 0 : -1;
      dropdown.innerHTML = renderRows(curItems, activeIdx);
      dropdown.classList.remove('hidden');
    }

    input.addEventListener('input', update);
    input.addEventListener('focus', function () { if (input.value.trim()) update(); });
    input.addEventListener('keydown', function (ev) {
      if (!curItems.length) return;
      if (ev.key === 'ArrowDown') {
        ev.preventDefault();
        activeIdx = (activeIdx + 1) % curItems.length;
        dropdown.innerHTML = renderRows(curItems, activeIdx);
        var selD = dropdown.querySelector('.selected');
        if (selD) selD.scrollIntoView({ block: 'nearest' });
      } else if (ev.key === 'ArrowUp') {
        ev.preventDefault();
        activeIdx = (activeIdx - 1 + curItems.length) % curItems.length;
        dropdown.innerHTML = renderRows(curItems, activeIdx);
        var selU = dropdown.querySelector('.selected');
        if (selU) selU.scrollIntoView({ block: 'nearest' });
      } else if (ev.key === 'Enter' && activeIdx >= 0) {
        ev.preventDefault();
        var sel = dropdown.querySelector('.selected');
        if (sel) sel.click();
      } else if (ev.key === 'Escape') {
        dropdown.classList.add('hidden');
      }
    });

    document.addEventListener('click', function (ev) {
      if (!input.contains(ev.target) && !dropdown.contains(ev.target)) {
        dropdown.classList.add('hidden');
      }
    });
  }

  function boot() {
    var input = document.getElementById('global-search');
    var dropdown = document.getElementById('search-results-dropdown');
    bindSearchBar(input, dropdown);

    document.addEventListener('keydown', function (ev) {
      if (!input) return;
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') {
        ev.preventDefault();
        input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(function () { input.focus(); input.select(); }, 60);
      } else if (ev.key === '/') {
        var tag = (document.activeElement && document.activeElement.tagName || '').toLowerCase();
        if (tag !== 'input' && tag !== 'textarea' && tag !== 'select') {
          ev.preventDefault();
          input.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(function () { input.focus(); }, 60);
        }
      }
    });

    window.KalSearch = { search: searchItems, renderRows: renderRows, resolveHref: resolveHref };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
