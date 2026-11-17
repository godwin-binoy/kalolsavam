/* Universal site-wide advanced search for the search bar on every page. */
(function () {
  'use strict';

  var SYNONYMS = {
    'drama': 'nadakam', 'mime': 'mookabhinayam', 'speech': 'prasangam',
    'elocution': 'prasangam', 'poem': 'kavitha padyam', 'recitation': 'padyam kavitha',
    'song': 'gaanam pattu', 'music': 'sangeetham', 'dance': 'nritham natyam',
    'drawing': 'chithra pencil', 'painting': 'colouring oil', 'watercolor': 'water colouring',
    'toilet': 'washroom', 'bathroom': 'toilet', 'wc': 'toilet', 'restroom': 'toilet',
    'food': 'dining oottupura', 'lunch': 'dining oottupura', 'eat': 'dining', 'meals': 'dining',
    'dress': 'green room', 'makeup': 'green room', 'costume': 'green room',
    'doctor': 'medical', 'ambulance': 'medical', 'hospital': 'medical', 'firstaid': 'medical',
    'result': 'results', 'score': 'results', 'marks': 'results', 'points': 'results',
    'ksrtc': 'bus', 'rickshaw': 'auto', 'taxi': 'auto',
    'photo': 'photos', 'picture': 'photos', 'gallery': 'photos'
  };

  function norm(s) {
    return String(s || '').toLowerCase().replace(/[\s\-_.:·,()]+/g, ' ').trim();
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
    var qComp = compact(rawQuery);
    var scored = [];

    for (var i = 0; i < data.length; i++) {
      var it = data[i];
      var tLow = (it.t || '').toLowerCase();
      var cLow = (it.c || '').toLowerCase();
      var dLow = (it.d || '').toLowerCase();
      var kLow = (it.k || '').toLowerCase();
      var hay = tLow + ' ' + cLow + ' ' + dLow + ' ' + kLow;
      var hayComp = compact(tLow + ' ' + kLow);

      var allMatch = true;
      var score = 0;

      for (var ti = 0; ti < tokens.length; ti++) {
        var tk = tokens[ti];
        var alt = SYNONYMS[tk] ? SYNONYMS[tk].split(' ') : [];
        var matchedTok = false;

        if (tLow.indexOf(tk) === 0) { score += 90; matchedTok = true; }
        else if (tLow.indexOf(tk) >= 0) { score += 45; matchedTok = true; }
        else if (cLow.indexOf(tk) >= 0) { score += 30; matchedTok = true; }
        else if (dLow.indexOf(tk) >= 0) { score += 18; matchedTok = true; }
        else if (kLow.indexOf(tk) >= 0 || hayComp.indexOf(compact(tk)) >= 0) { score += 12; matchedTok = true; }
        else if (alt.some(function (a) { return hay.indexOf(a) >= 0; })) { score += 10; matchedTok = true; }

        if (!matchedTok) { allMatch = false; break; }
      }

      if (!allMatch && qComp.length >= 4 && isSubseq(qComp, compact(tLow))) {
        score = 6;
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

    return scored.slice(0, maxResults || 12).map(function (s) { return s.item; });
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
