// SPIKE: puts a file page's trees in a rail to the left of the
// code, each level with its site, and its function cards in a
// rail to the right. Each function gets a bar on the code's
// right edge, from its def to its end, that opens its card. One
// tree or card is open at a time; opening one widens its rail,
// sliding the code away from it.
(function () {
  var code = document.querySelector('.code');
  if (!code) { return; }
  var box = code.parentElement;
  var trees = Array.prototype.slice.call(document.querySelectorAll('.tree'));
  var grids = Array.prototype.slice.call(document.querySelectorAll('.pathgrid'));
  var ccRail = document.createElement('div');
  ccRail.className = 'rail cc';
  var pcRail = document.createElement('div');
  pcRail.className = 'rail pc';
  var bars = grids.map(function (grid) {
    var bar = document.createElement('button');
    bar.type = 'button';
    bar.className = 'pathbar';
    bar.setAttribute('data-status', grid.getAttribute('data-status'));
    bar.setAttribute('aria-controls', grid.id);
    bar.setAttribute('aria-expanded', 'false');
    bar.title = grid.querySelector('.calls').title;
    return bar;
  });
  // Each method's def line, lit from its def to its bar, so the
  // two read as one bracket around the method.
  var bands = grids.map(function (grid) {
    var band = document.createElement('div');
    band.className = 'methodband';
    band.setAttribute('data-status', grid.getAttribute('data-status'));
    return band;
  });

  // The line-number button that opens tree.
  function buttonOf(tree) {
    return document.querySelector('button.lnum[aria-controls="' + tree.id + '"]');
  }

  // The bar that opens grid.
  function barOf(grid) {
    return bars[grids.indexOf(grid)];
  }

  // The number span of line n.
  function lineno(n) {
    return document.getElementById('L' + n);
  }

  // Element's top, middle and bottom relative to within's top.
  function spot(element, within) {
    var rect = element.getBoundingClientRect();
    var top = rect.top - within.getBoundingClientRect().top;
    return { top: top, middle: top + rect.height / 2, bottom: top + rect.height };
  }

  // Opens panel, a tree or a grid, alone; null closes all. Any
  // path shown or pinned goes with the grid it was in.
  function openOnly(panel) {
    pin(null);
    clear();
    trees.forEach(function (tree) {
      tree.hidden = tree !== panel;
      buttonOf(tree).setAttribute('aria-expanded', tree === panel ? 'true' : 'false');
    });
    grids.forEach(function (grid, i) {
      grid.hidden = grid !== panel;
      barOf(grid).setAttribute('aria-expanded', grid === panel ? 'true' : 'false');
      bands[i].classList.toggle('open', grid === panel);
    });
    var side = !panel ? '' : panel.classList.contains('tree') ? 'cc' : 'pc';
    document.body.setAttribute('data-open', side);
    slide(panel);
  }

  // Scrolls the page just enough to show all of panel when it
  // is a tree, eg one opened from a line near the bottom of the
  // window, so its last rows are not below the fold. Its first
  // row stays level with its site's line.
  function showWhole(panel) {
    if (panel && panel.classList.contains('tree')) {
      panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  // How long a rail takes to open or close, as style.css has it.
  var SLIDE_MS = 250;

  // Places everything on every frame while the rails slide, as
  // the bars and bands follow the code across, then shows all
  // of panel, the one just opened, once it is in its place.
  function slide(panel) {
    var end = performance.now() + SLIDE_MS + 50;
    function frame(now) {
      place();
      if (now < end) { requestAnimationFrame(frame); } else { showWhole(panel); }
    }
    requestAnimationFrame(frame);
  }

  // Sets an open tree's top so its first site's row, naming its
  // operator and path counts, is level with the first line of
  // its site's code.
  function placeTree(tree) {
    var block = buttonOf(tree).closest('.block');
    tree.style.top = '0px';
    var line = spot(block.querySelector('.src'), ccRail).middle;
    var row = spot(tree.querySelector('.site .row'), tree).middle;
    tree.style.top = (line - row) + 'px';
  }

  // Sets an open grid's top level with its def, its calls row
  // first and its decision rows straight after, with no gaps;
  // each row's label names its decision's line.
  // When the def has scrolled up under the sticky header, the
  // grid slides down to stay just below it, but never past its
  // method's last line.
  function placeGrid(grid) {
    var rows = Array.prototype.slice.call(grid.querySelectorAll('.prow'));
    var first = spot(lineno(grid.getAttribute('data-first')), pcRail);
    var last = spot(lineno(grid.getAttribute('data-last')), pcRail);
    var height = rows[0].getBoundingClientRect().height + 2;
    var tall = rows.length * height;
    var head = document.querySelector('.head').getBoundingClientRect().bottom;
    var below = head - pcRail.getBoundingClientRect().top + 8;
    var top = first.middle - height / 2;
    top = Math.max(top, Math.min(below, last.bottom - tall));
    grid.style.top = top + 'px';
    grid.style.height = tall + 'px';
    rows.forEach(function (row, i) {
      row.style.top = (i * height) + 'px';
    });
  }

  // Places panel, a tree or a grid.
  function placeOne(panel) {
    if (panel.classList.contains('tree')) { placeTree(panel); } else { placeGrid(panel); }
  }

  // Sets each bar beside the lines from its def to its end, on
  // the code pane's right edge, half into the gap before the
  // rail.
  // How many methods' lines enclose grid's: its bar sits one
  // lane further in for each, like nested brackets.
  function laneOf(grid) {
    var first = Number(grid.getAttribute('data-first'));
    var last = Number(grid.getAttribute('data-last'));
    return grids.filter(function (other) {
      var f = Number(other.getAttribute('data-first'));
      var l = Number(other.getAttribute('data-last'));
      return other !== grid && f <= first && last <= l;
    }).length;
  }

  // The x of a bar's middle, from the code pane's right edge,
  // for a method in lane.
  function barInset(lane) {
    return lane * 20;
  }

  // Sets each method's band over its def line, from the def's
  // column to its bar; it scrolls with the code, so is placed
  // again whenever the code scrolls.
  function placeBands() {
    var pane = code.getBoundingClientRect();
    bands.forEach(function (band, i) {
      var grid = grids[i];
      var src = srcOf(grid.getAttribute('data-first'));
      var text = src.firstChild;
      var col = Number(grid.getAttribute('data-col'));
      var range = document.createRange();
      range.setStart(text, Math.min(col, text.length));
      range.collapse(true);
      var left = range.getBoundingClientRect().left - pane.left + code.scrollLeft;
      var right = code.scrollLeft + code.clientWidth - barInset(laneOf(grid));
      var line = src.getBoundingClientRect();
      band.style.left = (left - 4) + 'px';
      band.style.width = Math.max(0, right - left + 4) + 'px';
      band.style.top = (line.top - pane.top + code.scrollTop) + 'px';
      band.style.height = line.height + 'px';
    });
  }

  function placeBars() {
    var edge = code.getBoundingClientRect().right - box.getBoundingClientRect().left;
    placeBands();
    bars.forEach(function (bar, i) {
      bar.style.left = (edge - 8 - barInset(laneOf(grids[i]))) + 'px';
      var first = spot(lineno(grids[i].getAttribute('data-first')), box);
      var last = spot(lineno(grids[i].getAttribute('data-last')), box);
      bar.style.top = first.top + 'px';
      bar.style.height = (last.bottom - first.top) + 'px';
    });
  }

  // Places the bars and whichever tree or grid is open.
  function place() {
    placeBars();
    trees.concat(grids).forEach(function (panel) {
      if (!panel.hidden) { placeOne(panel); }
    });
  }

  // The trees in the left rail, the grids in the right, the bars
  // on the code's right edge, nothing open.
  function beside() {
    box.insertBefore(ccRail, code);
    box.appendChild(pcRail);
    trees.forEach(function (tree) { ccRail.appendChild(tree); });
    grids.forEach(function (grid) { pcRail.appendChild(grid); });
    bars.forEach(function (bar) { box.appendChild(bar); });
    bands.forEach(function (band) { code.appendChild(band); });
    code.addEventListener('scroll', placeBands);
    openOnly(null);
    placeBars();
  }

  // The code span of line n, whether a plain line or one of a
  // site's lines.
  function srcOf(n) {
    var number = lineno(n);
    if (!number) { return null; }
    var button = number.closest('button.lnum');
    if (!button) { return number.parentElement.querySelector('.src'); }
    var index = Array.prototype.indexOf.call(button.querySelectorAll('.lineno'), number);
    return button.closest('.block').querySelectorAll('.srcs > .src')[index];
  }

  // [first, last] from a "first,last" attribute, null for "".
  function span(text) {
    return text ? text.split(',').map(Number) : null;
  }

  var lit = [];
  var chips = [];
  var hot = [];

  // Lights the code of every line in span, [first, last].
  function light(lines) {
    if (!lines) { return; }
    for (var n = lines[0]; n <= lines[1]; n++) {
      var src = srcOf(n);
      if (src) { src.classList.add('lit'); lit.push(src); }
    }
  }

  // Puts a T or F chip in the gutter of line n's row.
  function chip(n, text) {
    var number = lineno(n);
    if (!number) { return; }
    var nav = number.closest('.line, .block').querySelector('.nav');
    nav.setAttribute('data-chip', text);
    chips.push(nav);
  }

  // Undoes the lights and chips of the last path shown.
  function clear() {
    lit.forEach(function (src) { src.classList.remove('lit'); });
    chips.forEach(function (nav) { nav.removeAttribute('data-chip'); });
    hot.forEach(function (cell) { cell.classList.remove('hot'); });
    lit = [];
    chips = [];
    hot = [];
  }

  // Shows in the code the path in column col of grid: for each
  // decision it makes, its if lit with the arm taken and its
  // end, T lighting the then arm, F the else (none without
  // one), and a T or F chip in the gutter. Decisions after a
  // path leaves early stay unlit.
  function show(grid, col) {
    clear();
    grid.querySelectorAll('.prow').forEach(function (row) {
      var cell = row.querySelectorAll('.pcell')[col];
      cell.classList.add('hot');
      hot.push(cell);
      if (row.classList.contains('calls') || cell.classList.contains('ended')) { return; }
      var taken = cell.classList.contains('true');
      light(span(row.getAttribute('data-head')));
      light(span(row.getAttribute(taken ? 'data-then' : 'data-else')));
      light(span(row.getAttribute('data-end')));
      chip(Number(row.getAttribute('data-line')), taken ? 'T' : 'F');
    });
  }

  // The pinned path, { grid, col }, shown whenever no other is
  // hovered; null when none is pinned.
  var pinned = null;

  // The grid and column of a cell.
  function columnOf(cell) {
    var cells = Array.prototype.slice.call(cell.parentElement.querySelectorAll('.pcell'));
    return { grid: cell.closest('.pathgrid'), col: cells.indexOf(cell) };
  }

  // Pins column, or unpins with null, outlining the pinned
  // column's cells.
  function pin(column) {
    document.querySelectorAll('.pcell.pinned').forEach(function (cell) {
      cell.classList.remove('pinned');
    });
    pinned = column;
    if (!column) { return; }
    column.grid.querySelectorAll('.prow').forEach(function (row) {
      row.querySelectorAll('.pcell')[column.col].classList.add('pinned');
    });
  }

  // Shows the pinned path, or nothing when none is pinned.
  function showPinned() {
    if (pinned) { show(pinned.grid, pinned.col); } else { clear(); }
  }

  pcRail.addEventListener('mouseover', function (event) {
    var cell = event.target.closest('.pathgrid:not(.statements) .pcell');
    if (!cell) { return; }
    var column = columnOf(cell);
    show(column.grid, column.col);
  });
  pcRail.addEventListener('mouseleave', showPinned);

  // The code spans whose characters are marked, with the text
  // each had before.
  var markedSrcs = [];

  // The length of text's leading whitespace.
  function indentOf(text) {
    return text.match(/^\s*/)[0].length;
  }

  // Puts back every span marked as it was, site tints and all.
  function unmarkChars() {
    markedSrcs.forEach(function (entry) { entry.src.innerHTML = entry.html; });
    markedSrcs = [];
  }

  // Tints each site's own characters by its status, gaps when
  // any of its paths was never taken, rather than its whole
  // lines; where sites overlap, gaps wins.
  function tintSites() {
    var perLine = {};
    document.querySelectorAll('.tree .site').forEach(function (site) {
      var row = site.querySelector('.row[data-at]');
      if (!row) { return; }
      var at = row.getAttribute('data-at').split(',').map(Number);
      var gaps = site.querySelector('.count.never') !== null;
      for (var n = at[0]; n <= at[2]; n++) {
        (perLine[n] = perLine[n] || []).push({
          from: n === at[0] ? at[1] : -1, to: n === at[2] ? at[3] : Infinity,
          status: gaps ? 'gaps' : 'covered'
        });
      }
    });
    Object.keys(perLine).forEach(function (n) {
      var src = srcOf(n);
      if (!src) { return; }
      var text = src.textContent;
      var marks = text.split('').map(function () { return null; });
      perLine[n].forEach(function (span) {
        // A continuation line (from -1) is tinted from its first
        // character after the indent.
        var from = span.from < 0 ? indentOf(text) : span.from;
        for (var i = from; i < Math.min(span.to, text.length); i++) {
          if (marks[i] !== 'gaps') { marks[i] = span.status; }
        }
      });
      src.textContent = '';
      var i = 0;
      while (i < text.length) {
        var j = i;
        while (j < text.length && marks[j] === marks[i]) { j++; }
        var part = text.slice(i, j);
        if (marks[i]) {
          var mark = document.createElement('mark');
          mark.className = 'site';
          mark.setAttribute('data-status', marks[i]);
          mark.textContent = part;
          src.appendChild(mark);
        } else {
          src.appendChild(document.createTextNode(part));
        }
        i = j;
      }
    });
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
      var mark = document.createElement('mark');
      mark.className = 'chars';
      mark.textContent = text.slice(from, to);
      src.textContent = text.slice(0, from);
      src.appendChild(mark);
      src.appendChild(document.createTextNode(text.slice(to)));
    }
    reveal(document.querySelectorAll('mark.chars'));
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

  // Hovering a tree's row marks in the code the characters of
  // its operand, or of its operator's whole condition.
  var markedRow = null;
  ccRail.addEventListener('mouseover', function (event) {
    var row = event.target.closest('.tree .row[data-at]');
    if (row === markedRow) { return; }
    markedRow = row;
    if (!row) { unmarkChars(); return; }
    var at = row.getAttribute('data-at').split(',').map(Number);
    markChars(at[0], at[1], at[2], at[3]);
  });
  ccRail.addEventListener('mouseleave', function () {
    markedRow = null;
    unmarkChars();
  });

  // A click on a site's row in a function card opens the tree of
  // the block holding its line, as that block's button does.
  pcRail.addEventListener('click', function (event) {
    var row = event.target.closest('.statements .prow.site');
    if (!row) { return; }
    var block = lineno(row.getAttribute('data-line')).closest('.block');
    var button = block && block.querySelector('button.lnum[aria-controls]');
    if (button) { openOnly(document.getElementById(button.getAttribute('aria-controls'))); }
  });

  // A click on a cell pins its column, or unpins it when it is
  // the one pinned.
  pcRail.addEventListener('click', function (event) {
    var cell = event.target.closest('.pathgrid:not(.statements) .pcell');
    if (!cell) { return; }
    var column = columnOf(cell);
    var same = pinned && pinned.grid === column.grid && pinned.col === column.col;
    pin(same ? null : column);
    show(column.grid, column.col);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && pinned) { pin(null); clear(); }
  });

  // Opening one tree or grid closes the others; a click on a
  // site's code acts as one on its button; a gap arrow opens
  // the tree of the line it jumps to.
  document.addEventListener('click', function (event) {
    var bar = event.target.closest('.pathbar');
    if (bar) {
      var grid = document.getElementById(bar.getAttribute('aria-controls'));
      openOnly(grid.hidden ? grid : null);
      return;
    }
    var line = event.target.closest('.line');
    if (line && !event.target.closest('button, a')) {
      // A click on a method's def line acts as one on its bar.
      var number = line.querySelector('.lineno').getAttribute('data-line');
      var method = grids.filter(function (g) { return g.getAttribute('data-first') === number; })[0];
      if (method) { openOnly(method.hidden ? method : null); }
      return;
    }
    var block = event.target.closest('.block');
    if (block && !event.target.closest('button, a')) {
      block.querySelector('button[aria-controls]').click();
      return;
    }
    var button = event.target.closest('button.lnum');
    if (button) {
      var tree = document.getElementById(button.getAttribute('aria-controls'));
      openOnly(tree.hidden ? null : tree);
      return;
    }
    var arrow = event.target.closest('.nav a, a.jump');
    if (arrow) {
      var target = document.getElementById('tree-' + arrow.hash.slice(2));
      if (target) { openOnly(target); }
    }
  });

  window.addEventListener('resize', place);
  window.addEventListener('scroll', function () {
    grids.forEach(function (grid) { if (!grid.hidden) { placeGrid(grid); } });
  });

  // Puts every site's jump in the header into one row, labelled
  // Conditions, in line order; each chip's edge shows its status.
  function oneJumpRow() {
    var lists = document.querySelectorAll('.jump-list');
    if (lists.length === 0) { return; }
    var jumps = Array.prototype.slice.call(document.querySelectorAll('a.jump'));
    jumps.sort(function (a, b) { return Number(a.textContent) - Number(b.textContent); });
    var row = lists[0];
    row.removeAttribute('data-jumps');
    row.querySelector('.jump-label').textContent = 'Conditions';
    jumps.forEach(function (jump) { row.appendChild(jump); });
    for (var i = 1; i < lists.length; i++) { lists[i].remove(); }
  }

  // The cell kind that draws each of a tree's branch glyphs.
  // Built from char codes (vertical, tee, elbow, horizontal) so this
  // file stays ASCII.
  var BRANCH_CELLS = {};
  BRANCH_CELLS[String.fromCharCode(0x2502)] = 'v';
  BRANCH_CELLS[String.fromCharCode(0x251C)] = 't';
  BRANCH_CELLS[String.fromCharCode(0x2514)] = 'l';
  BRANCH_CELLS[String.fromCharCode(0x2500)] = 'h';

  // Redraws each tree's branch glyphs as cells a whole row tall,
  // whose lines run edge to edge, so the branches join from row
  // to row as the glyphs, shorter than a row, cannot.
  function drawBranches() {
    document.querySelectorAll('.tree .branch').forEach(function (branch) {
      var text = branch.textContent;
      branch.setAttribute('aria-hidden', 'true');
      branch.textContent = '';
      text.split('').forEach(function (ch) {
        var cell = document.createElement('span');
        cell.className = 'bx';
        cell.setAttribute('data-bx', BRANCH_CELLS[ch] || 's');
        branch.appendChild(cell);
      });
    });
  }

  document.body.setAttribute('data-layout', 'beside');
  drawBranches();
  oneJumpRow();
  tintSites();
  beside();
})();
