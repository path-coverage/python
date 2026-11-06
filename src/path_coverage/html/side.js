// The behaviour of a file's page: its cards sit in the rail left
// of the code, one open at a time, level with its first line. A
// method's def number opens its card, unfolding its body; a loose
// site's button, outside every method, opens its lines' top card.
// The page's markup, from the Ruby, already marks every method's
// lines, numbers and rows; this only opens, closes and places.
(function () {
  var code = document.querySelector('.code');
  if (!code) { return; }
  var box = code.parentElement;
  var rail = document.querySelector('.rail');
  var divider = document.querySelector('.divider');
  var grids = Array.prototype.slice.call(document.querySelectorAll('.pathgrid'));

  // True for a top card, of sites outside every method.
  function isTop(grid) {
    return grid.classList.contains('top-level');
  }

  // A card's first and last lines.
  function firstOf(grid) { return Number(grid.getAttribute('data-first')); }
  function lastOf(grid) { return Number(grid.getAttribute('data-last')); }

  // The number span of line n.
  function lineno(n) {
    return document.getElementById('L' + n);
  }

  // The row, a line or a loose site's block, holding line n.
  function rowOf(n) {
    return lineno(n).closest('.line, .block');
  }

  // The code span of line n, whether a line's own or one of a
  // loose site's lines.
  function srcOf(n) {
    var number = lineno(n);
    if (!number) { return null; }
    var button = number.closest('button.lnum');
    if (!button) { return number.parentElement.querySelector('.src'); }
    var index = Array.prototype.indexOf.call(button.querySelectorAll('.lineno'), number);
    return button.closest('.block').querySelectorAll('.srcs > .src')[index];
  }

  // The code of each method's lines, from its def to its end,
  // which thickens its stripe while its card is open; none for a
  // top card.
  var methodSrcs = grids.map(function (grid) {
    if (isTop(grid)) { return []; }
    var srcs = [];
    for (var n = firstOf(grid); n <= lastOf(grid); n++) { srcs.push(srcOf(n)); }
    return srcs;
  });

  // The rows of each method's body, after its def line to its end,
  // folded under its def line while its card is closed; a row
  // holding its def line too is never folded. None for a top card.
  var methodRows = grids.map(function (grid) {
    if (isTop(grid)) { return []; }
    var def = rowOf(firstOf(grid));
    var rows = [];
    for (var n = firstOf(grid) + 1; n <= lastOf(grid); n++) {
      var row = rowOf(n);
      if (row !== def && rows.indexOf(row) < 0) { rows.push(row); }
    }
    return rows;
  });

  // The def number of each method's card, which opens it; null for
  // a top card, which its site's button opens.
  var defs = grids.map(function (grid) {
    return isTop(grid) ? null : lineno(firstOf(grid));
  });

  // The loose button opening each top card; null for a method's.
  var buttons = grids.map(function (grid) {
    return isTop(grid) ? document.querySelector('button.lnum[aria-controls="' + grid.id + '"]') : null;
  });

  // Element's top, middle and bottom relative to within's top.
  function spot(element, within) {
    var rect = element.getBoundingClientRect();
    var top = rect.top - within.getBoundingClientRect().top;
    return { top: top, middle: top + rect.height / 2, bottom: top + rect.height };
  }

  // Opens grid alone, null closing all: a method's card opens its
  // body, every other method's folded; its def number, or its
  // site's button, says it is open.
  function openOnly(open) {
    clear();
    grids.forEach(function (grid, i) {
      var shown = grid === open;
      grid.hidden = !shown;
      methodSrcs[i].forEach(function (src) { src.classList.toggle('method-open', shown); });
      (defs[i] || buttons[i]).setAttribute('aria-expanded', String(shown));
    });
    foldBodies(grids.indexOf(open));
    document.body.toggleAttribute('data-open', open !== null);
    place();
    stickDef();
  }

  // True when the method of grids[inner] is defined inside that of
  // grids[outer], eg a def inside a def.
  function nests(inner, outer) {
    return firstOf(grids[outer]) < firstOf(grids[inner]) && lastOf(grids[inner]) <= lastOf(grids[outer]);
  }

  // Folds every method's body but that of grids[open], none for -1:
  // its rows show, but for those of any method inside it, which stay
  // folded under their def lines; and its def line shows, with those
  // of the methods it is inside, though they lie in folded bodies.
  function foldBodies(open) {
    var shown = [];
    if (open >= 0) {
      shown = methodRows[open].filter(function (row) {
        return !grids.some(function (grid, j) {
          return nests(j, open) && methodRows[j].indexOf(row) >= 0;
        });
      });
      grids.forEach(function (grid, j) {
        if (j === open || nests(open, j)) { shown.push(rowOf(firstOf(grid))); }
      });
    }
    methodRows.forEach(function (rows) {
      rows.forEach(function (row) { row.classList.toggle('method-folded', shown.indexOf(row) < 0); });
    });
  }

  // The narrowest the rail drags to, and the narrowest the code
  // beside it is left.
  var RAIL_MIN = 240;
  var CODE_MIN = 320;
  var RAIL_KEY = 'path_coverage.rail';

  // Sets the rail to width pixels, kept within its bounds, and
  // places the open card again beside it.
  function setRail(width) {
    var most = box.getBoundingClientRect().width - CODE_MIN;
    var wide = Math.round(Math.max(RAIL_MIN, Math.min(most, width)));
    document.body.style.setProperty('--rail', wide + 'px');
    place();
    return wide;
  }

  // Dragging the divider sets the rail's width, kept in the
  // browser, where it can be, for the next page.
  divider.addEventListener('pointerdown', function (event) {
    divider.setPointerCapture(event.pointerId);
    divider.classList.add('dragging');
    document.body.classList.add('dragging');
    event.preventDefault();
  });
  divider.addEventListener('pointermove', function (event) {
    if (!divider.classList.contains('dragging')) { return; }
    setRail(event.clientX - box.getBoundingClientRect().left - 6);
  });
  divider.addEventListener('pointerup', function (event) {
    divider.releasePointerCapture(event.pointerId);
    divider.classList.remove('dragging');
    document.body.classList.remove('dragging');
    var wide = parseInt(document.body.style.getPropertyValue('--rail'), 10);
    try { window.localStorage.setItem(RAIL_KEY, String(wide)); } catch (e) { /* this page only */ }
  });

  // The rail's width kept from an earlier page, if any.
  function keptRail() {
    try { return parseInt(window.localStorage.getItem(RAIL_KEY), 10); } catch (e) { return NaN; }
  }

  // Sets an open card's top so its title row is level with its
  // first line; its rows, and any fold open among them, flow down
  // it. When its first line has scrolled up under the sticky
  // header, the card slides down to stay just below it, but never
  // past its last line. The rail stretches to the card's bottom,
  // as the card, placed absolutely, adds no height of its own, so
  // the box grows to show a card taller than the code.
  function placeGrid(grid) {
    var first = spot(lineno(firstOf(grid)), rail);
    var last = spot(lineno(lastOf(grid)), rail);
    var title = spot(grid.querySelector('.prow'), grid).middle;
    var tall = grid.getBoundingClientRect().height;
    var head = document.querySelector('.head').getBoundingClientRect().bottom;
    var below = head - rail.getBoundingClientRect().top + 8;
    var top = first.middle - title;
    top = Math.max(top, Math.min(below, last.bottom - tall));
    grid.style.top = top + 'px';
    rail.style.minHeight = (top + tall) + 'px';
  }

  // Places whichever card is open; with none open the rail is
  // only as tall as the code.
  function place() {
    rail.style.minHeight = '';
    grids.forEach(function (grid) { if (!grid.hidden) { placeGrid(grid); } });
  }

  // The code spans lit for the card row hovered.
  var lit = [];

  // Lights the code of every line in span, [first, last].
  function light(lines) {
    for (var n = lines[0]; n <= lines[1]; n++) {
      var src = srcOf(n);
      if (src) { src.classList.add('lit'); lit.push(src); }
    }
  }

  // Unlights the code lit.
  function clear() {
    lit.forEach(function (src) { src.classList.remove('lit'); });
    lit = [];
  }

  rail.addEventListener('mouseleave', clear);

  // The code spans whose characters are marked, with the text
  // each had before.
  var markedSrcs = [];

  // The length of text's leading whitespace.
  function indentOf(text) {
    return text.match(/^\s*/)[0].length;
  }

  // Puts back every span marked as it was.
  function unmarkChars() {
    markedSrcs.forEach(function (entry) { entry.src.innerHTML = entry.html; });
    markedSrcs = [];
  }

  // Marks the characters from line l1, column c1 to line l2,
  // column c2, each line's part in a mark of its own.
  function markChars(l1, c1, l2, c2) {
    unmarkChars();
    for (var n = l1; n <= l2; n++) {
      var src = srcOf(n);
      if (!src) { continue; }
      var text = src.textContent;
      var from = n === l1 ? c1 : indentOf(text);
      var to = n === l2 ? c2 : text.length;
      markedSrcs.push({ src: src, html: src.innerHTML });
      paint(src, function (i) { return i >= from && i < to ? 'chars' : null; }, function () {
        var mark = document.createElement('mark');
        mark.className = 'chars';
        return mark;
      });
    }
    reveal(document.querySelectorAll('mark.chars'));
  }

  // The colour class of each of src's characters, the class of the
  // token span it is in, null for one in none.
  function tokensOf(src) {
    var tokens = [];
    var walker = document.createTreeWalker(src, NodeFilter.SHOW_TEXT);
    for (var node = walker.nextNode(); node; node = walker.nextNode()) {
      var parent = node.parentNode;
      var css = parent !== src && parent.tagName === 'SPAN' ? parent.className : null;
      for (var i = 0; i < node.length; i++) { tokens.push(css); }
    }
    return tokens;
  }

  // Rebuilds src's code, each run of characters keyAt gives one key
  // to in the element wrap makes of that key, the others bare, every
  // character still in a span of its token's colour class.
  function paint(src, keyAt, wrap) {
    var text = src.textContent;
    var tokens = tokensOf(src);
    src.textContent = '';
    var i = 0;
    while (i < text.length) {
      var j = i;
      var key = keyAt(i);
      while (j < text.length && keyAt(j) === key) { j++; }
      var holder = key ? wrap(key) : src;
      appendTokens(holder, text, tokens, i, j);
      if (key) { src.appendChild(holder); }
      i = j;
    }
  }

  // Appends text's characters i to j to holder, each run of one
  // token class in a span of that class, the rest bare.
  function appendTokens(holder, text, tokens, i, j) {
    var k = i;
    while (k < j) {
      var m = k;
      while (m < j && tokens[m] === tokens[k]) { m++; }
      var part = text.slice(k, m);
      if (tokens[k]) {
        var span = document.createElement('span');
        span.className = tokens[k];
        span.textContent = part;
        holder.appendChild(span);
      } else {
        holder.appendChild(document.createTextNode(part));
      }
      k = m;
    }
  }

  // The width of the code pane's left columns (gap arrows and
  // line numbers), which code scrolls under.
  var GUTTER = 108;

  // Scrolls the code pane sideways so all of marks are in view,
  // their start kept in view when they are wider than the pane.
  function reveal(marks) {
    if (marks.length === 0) { return; }
    var pane = code.getBoundingClientRect();
    var left = Infinity;
    var right = -Infinity;
    marks.forEach(function (mark) {
      var rect = mark.getBoundingClientRect();
      left = Math.min(left, rect.left);
      right = Math.max(right, rect.right);
    });
    var shift = 0;
    if (right > pane.right - 8) { shift = right - pane.right + 8; }
    if (left - shift < pane.left + GUTTER) { shift = left - pane.left - GUTTER; }
    if (shift !== 0) { code.scrollBy({ left: shift, behavior: 'smooth' }); }
  }

  // Hovering a row of a fold in a card marks in the code the
  // characters of its operand, or of its operator's whole
  // condition.
  var markedRow = null;
  rail.addEventListener('mouseover', function (event) {
    var row = event.target.closest('.fold .row[data-at]');
    if (row === markedRow) { return; }
    markedRow = row;
    if (!row) { unmarkChars(); return; }
    var at = row.getAttribute('data-at').split(',').map(Number);
    markChars(at[0], at[1], at[2], at[3]);
  });
  rail.addEventListener('mouseleave', function () {
    markedRow = null;
    unmarkChars();
  });

  // Hovering a statement's row in a card lights its line in the
  // code, scrolling the page only when that line is out of view.
  var litRow = null;
  rail.addEventListener('mouseover', function (event) {
    var row = event.target.closest('.statements .prow[data-line]:not(.calls)');
    if (row === litRow) { return; }
    litRow = row;
    clear();
    if (!row) { return; }
    var n = Number(row.getAttribute('data-line'));
    light([n, n]);
    // A number's scroll margin keeps it clear of the sticky header
    // and the def line stuck below it.
    lineno(n).scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });
  rail.addEventListener('mouseleave', function () { litRow = null; });

  // A click on a site's row in a card unfolds that site's tree in
  // the row's place, folding up any other open; a click on the row
  // of the one open, or on its fold's first row, which stands in
  // the row's place, folds it back.
  rail.addEventListener('click', function (event) {
    if (event.target.closest('.fold .site > .row:first-child')) { unfold(null); return; }
    var row = event.target.closest('.statements .prow.site');
    var fold = row && row.nextElementSibling;
    if (!fold || !fold.classList.contains('fold')) { return; }
    unfold(fold.hidden ? fold : null);
  });

  // Shows fold alone, null folding them all up, the arrow of each
  // site's row pointing up while its fold shows; then places the
  // open card again, as its height has changed.
  function unfold(fold) {
    rail.querySelectorAll('.fold').forEach(function (each) {
      each.hidden = each !== fold;
      var arrow = each.previousElementSibling.querySelector('.fold-arrow');
      arrow.setAttribute('aria-expanded', String(each === fold));
    });
    place();
  }

  // Hovering code in the open card's lines unfolds that card's fold
  // holding the innermost row whose code is under the pointer, alone,
  // lighting that row; code in no fold, eg x = 42, lights its
  // statement's row in the card instead, every fold folded. Each
  // waits a pause, so sweeping the pointer along a line does not
  // flicker. Leaving the code leaves what was lit lit. A card that
  // is not open is left shut, as opening it would fold other
  // methods' code away from under the pointer.
  var HOVER_PAUSE = 80;
  var hoverTimer = null;
  var hoveredRow = null;
  code.addEventListener('mousemove', function (event) {
    clearTimeout(hoverTimer);
    var x = event.clientX;
    var y = event.clientY;
    hoverTimer = setTimeout(function () { hoverAt(x, y); }, HOVER_PAUSE);
  });
  code.addEventListener('mouseleave', function () { clearTimeout(hoverTimer); });

  // Shows, in the open card, the row of the code at x, y, if any.
  function hoverAt(x, y) {
    var at = caretAt(x, y);
    var open = grids.filter(function (grid) { return !grid.hidden; })[0];
    if (!at || !open) { return; }
    var row = innermostRow(open, at.line, at.column);
    if (row) {
      if (row !== hoveredRow) { showRow(row); }
      return;
    }
    var statement = statementRow(open, at.line, at.column);
    if (statement && statement !== hoveredRow) { showStatement(statement); }
  }

  // The row of grid's statement holding line and column: of those
  // starting on line, the last starting at or before column, or the
  // first, eg the ?: row for the x = of x = a ? 1 : 2; null for none.
  function statementRow(grid, line, column) {
    var rows = grid.querySelectorAll('.prow[data-line="' + line + '"]:not(.calls)');
    var best = rows[0] || null;
    rows.forEach(function (row) {
      var label = row.querySelector('.plabel').textContent;
      if (Number(label.split(':')[1]) <= column) { best = row; }
    });
    return best;
  }

  // Lights row, a statement's, alone, every fold folded.
  function showStatement(row) {
    if (hoveredRow) { hoveredRow.classList.remove('hovered'); }
    hoveredRow = row;
    unfold(null);
    row.classList.add('hovered');
  }

  // The line and column of the code character at x, y; null when
  // no code is there.
  function caretAt(x, y) {
    var node;
    var offset;
    if (document.caretRangeFromPoint) {
      var range = document.caretRangeFromPoint(x, y);
      if (!range) { return null; }
      node = range.startContainer;
      offset = range.startOffset;
    } else if (document.caretPositionFromPoint) {
      var caret = document.caretPositionFromPoint(x, y);
      if (!caret) { return null; }
      node = caret.offsetNode;
      offset = caret.offset;
    } else {
      return null;
    }
    var element = node.nodeType === 1 ? node : node.parentElement;
    var src = element && element.closest('.src');
    if (!src) { return null; }
    var before = document.createRange();
    before.setStart(src, 0);
    before.setEnd(node, offset);
    return { line: lineOf(src), column: before.toString().length };
  }

  // The number of the line whose code is src, a line's own or one of
  // a loose site's lines.
  function lineOf(src) {
    var block = src.closest('.block');
    if (!block) { return Number(src.parentElement.querySelector('.lineno').id.slice(1)); }
    var index = Array.prototype.indexOf.call(block.querySelectorAll('.srcs > .src'), src);
    return Number(block.querySelectorAll('.lineno')[index].id.slice(1));
  }

  // The row, of grid's folds, whose code, its data-at, or whose
  // else keyword, its data-else, holds line and column and is the
  // shortest so; null for none.
  function innermostRow(grid, line, column) {
    var best = null;
    var shortest = Infinity;
    grid.querySelectorAll('.fold .row[data-at], .fold .row[data-else]').forEach(function (row) {
      ['data-at', 'data-else'].forEach(function (name) {
        var span = row.getAttribute(name);
        if (!span) { return; }
        var at = span.split(',').map(Number);
        if (!holds(at, line, column)) { return; }
        var size = (at[2] - at[0]) * 100000 + (at[3] - at[1]);
        if (size < shortest) { best = row; shortest = size; }
      });
    });
    return best;
  }

  // True when at, [line, column, end line, end column], holds the
  // character at line and column.
  function holds(at, line, column) {
    var from = line > at[0] || (line === at[0] && column >= at[1]);
    var to = line < at[2] || (line === at[2] && column < at[3]);
    return from && to;
  }

  // Unfolds row's fold alone and lights row, its text scrolled back
  // to its start, unlighting the row lit before.
  function showRow(row) {
    if (hoveredRow) { hoveredRow.classList.remove('hovered'); }
    hoveredRow = row;
    var fold = row.closest('.fold');
    if (fold.hidden) { unfold(fold); }
    row.classList.add('hovered');
    var text = row.querySelector('.text');
    if (text) { text.scrollLeft = 0; }
  }

  // Opening one card closes the others, and a click never closes
  // the one open, so the rail always shows one. A click on a def
  // line opens its method's card; one on a loose site's lines opens
  // their top card; a gutter arrow or a header jump opens the card
  // at the line it jumps to.
  document.addEventListener('click', function (event) {
    var link = event.target.closest('.nav a, a.jump');
    if (link) { openOnly(document.getElementById('paths-' + link.hash.slice(2))); return; }
    if (event.target.closest('a')) { return; }
    var loose = event.target.closest('.block');
    var button = loose && loose.querySelector('button.lnum.loose');
    if (button) { openOnly(document.getElementById(button.getAttribute('aria-controls'))); return; }
    var row = event.target.closest('.line, .block');
    var number = row && row.querySelector('.lineno.mdef');
    if (number) { openOnly(grids[defs.indexOf(number)]); }
  });

  window.addEventListener('resize', place);

  // The card of the innermost method whose def to end hold line n,
  // or of the top card holding it, so a linked line in a body is
  // never left folded away; null when none holds n.
  function cardOf(n) {
    var holding = grids.filter(function (grid) { return firstOf(grid) <= n && n <= lastOf(grid); });
    return holding.length ? holding[holding.length - 1] : null;
  }

  // On a page at a linked line, eg #L8, opens the card holding it.
  // Otherwise opens the first card with gaps, or, with none, the
  // first card, its first line scrolled into view, so one is always
  // open, every other method's body folded under its def line;
  // opens nothing only on a page with no card at all.
  function openFirst() {
    var linked = /^#L(\d+)$/.exec(window.location.hash);
    var own = linked && cardOf(Number(linked[1]));
    if (own) { openOnly(own); return; }
    var jump = document.querySelector('.jump-list a.jump');
    var card = jump ? cardOf(Number(jump.hash.slice(2))) : grids[0];
    if (!card) { openOnly(null); return; }
    lineno(firstOf(card)).scrollIntoView({ block: 'center' });
    openOnly(card);
  }

  // Keeps the header, the open card and its def line in view as the
  // page scrolls, and as a pinch-zoomed view pans or zooms. Pinch
  // zoom pans a lens over the page, which CSS sticky ignores, so
  // the header is shifted down by the lens's pan; the card and def
  // line then follow the header's drawn bottom.
  function followView() {
    var pan = window.visualViewport ? window.visualViewport.offsetTop : 0;
    document.querySelector('.head').style.transform = pan > 0 ? 'translateY(' + pan + 'px)' : '';
    place();
    stickDef();
  }
  window.addEventListener('scroll', followView);
  window.addEventListener('resize', stickDef);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('scroll', followView);
    window.visualViewport.addEventListener('resize', followView);
  }

  // Keeps the def line of the open method in view: once it would
  // scroll up under the sticky header, it is shifted down to sit
  // just below it, over the body lines passing beneath, but never
  // past the method's last line. The code pane scrolls sideways, so
  // CSS sticky, which would stick within the pane, cannot do this.
  function stickDef() {
    grids.forEach(function (grid) {
      var row = rowOf(firstOf(grid));
      row.style.transform = '';
      row.classList.remove('def-stuck');
      if (grid.hidden) { return; }
      var head = document.querySelector('.head').getBoundingClientRect().bottom;
      var rect = row.getBoundingClientRect();
      var last = lineno(lastOf(grid)).getBoundingClientRect();
      var shift = Math.min(head - rect.top, last.bottom - rect.bottom);
      if (shift <= 0) { return; }
      row.style.transform = 'translateY(' + shift + 'px)';
      row.classList.add('def-stuck');
    });
  }

  var kept = keptRail();
  if (kept > 0) { setRail(kept); }
  openFirst();
})();
