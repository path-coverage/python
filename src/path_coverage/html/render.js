// Draws a path coverage page from its data, window.pathCoverage, as
// schema.json has it, into the page's <main>. It runs before the
// page's other scripts, which then find the page as they would had
// it been written whole. A port computes; this only draws.
(function () {
  'use strict';

  var SCHEMA = 1;
  var data = window.pathCoverage;
  if (!data || data.schema !== SCHEMA) {
    throw new Error('path coverage: page data of schema ' +
      (data && data.schema) + ', but render.js draws schema ' + SCHEMA);
  }

  // text, escaped for HTML.
  function esc(text) {
    return String(text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // code, {text, tokens}, escaped, each token's range, its columns
  // counting characters, in a span of its class.
  function painted(code) {
    var chars = Array.from(code.text);
    var at = 0;
    var out = '';
    code.tokens.forEach(function (token) {
      out += esc(chars.slice(at, token[0]).join('')) +
        '<span class="' + token[2] + '">' +
        esc(chars.slice(token[0], token[1]).join('')) + '</span>';
      at = token[1];
    });
    return out + esc(chars.slice(at).join(''));
  }

  // ---------------------------------------------------------------
  // The index page.

  // A table cell, sorted by sort, showing content, with title as its
  // hover and css as its class, each when given.
  function td(sort, content, title, css) {
    var klass = css ? ' class="' + css + '"' : '';
    var hover = title ? ' title="' + title + '"' : '';
    return '<td' + klass + ' data-sort="' + esc(sort) + '"' + hover + '>' +
      content + '</td>';
  }

  // Why a total of no paths shows no percent.
  var NONE = 'no method with two or more decisions';

  // The cells after a row's file: its sites, then its taken, / of and
  // percent within each method.
  function counts(row) {
    var taken = row.methods[0];
    var possible = row.methods[1];
    var percent = row.percent === null
      ? td('', '-', NONE, 'percent')
      : td(row.percent, row.percent + '%', null, 'percent');
    return td(row.sites, row.sites) +
      td(taken, taken, null, 'taken') +
      td(possible, '/ ' + possible, null, 'of') + percent;
  }

  // The heading row of a files table, every column sortable.
  function headRow() {
    var heading = function (attrs, column, type, label) {
      return '<th' + attrs + ' aria-sort="none"><button type="button"' +
        ' data-column="' + column + '" data-type="' + type + '">' +
        label + '</button></th>';
    };
    var parts = [['taken', 'taken'], ['of', '/ of'], ['percent', '%']];
    var cells = [heading('', 0, 'text', 'File'),
      heading(' class="num"', 1, 'number', 'Sites')].concat(
      parts.map(function (part, i) {
        return heading(' class="' + part[0] + '"', 2 + i, 'number', part[1]);
      }));
    return '<tr>\n' + cells.join('\n') + '\n</tr>';
  }

  // The index-th tab's table; any but the first hidden, only the
  // first giving its rows ids, as the others repeat its rows.
  function table(index, shown) {
    var anchored = index === 0;
    var body = shown.rows.map(function (row) {
      var path = esc(row.path);
      var link = '<a href="files/' + path + '.html">' + path + '</a>';
      var id = anchored ? ' id="row-' + path + '"' : '';
      return '<tr' + id + '>' + td(row.path, link) + counts(row) + '</tr>';
    }).join('\n');
    var hidden = anchored ? '' : ' hidden="hidden"';
    return [
      '<table class="files" id="files-' + index + '" role="tabpanel"' +
        hidden + '>',
      '<thead>\n' + headRow() + '\n</thead>',
      '<tbody>\n' + body + '\n</tbody>',
      '<tfoot>\n<tr>' + td('Total', 'Total') + counts(shown.total) +
        '</tr>\n</tfoot>',
      '</table>'
    ].join('\n');
  }

  // The tab bar, a tab per table, the first selected; none for one
  // table.
  function tabs(tables) {
    if (tables.length < 2) { return ''; }
    var buttons = tables.map(function (shown, i) {
      return '<button type="button" role="tab" aria-selected="' +
        (i === 0) + '" aria-controls="files-' + i + '">' +
        esc(shown.name) + '</button>';
    });
    return '<nav class="tabs" role="tablist" aria-label="Groups">' +
      buttons.join('') + '</nav>';
  }

  // The paragraph naming the operators ignored; none when none are.
  function ignored(names) {
    if (names.length === 0) { return ''; }
    return '<p class="ignored" data-ignored="">' +
      esc('Ignored: ' + names.join(', ')) + '</p>';
  }

  // The index page's <main>.
  function indexPage(page) {
    var tables = page.tables.map(function (shown, i) {
      return table(i, shown);
    }).join('\n');
    return '\n<header class="head" data-head="">\n' +
      '<div class="top"><h1 class="title">Path coverage</h1>' +
      '<button type="button" class="theme" aria-label="Light or dark">' +
      '</button></div>\n</header>\n' + tabs(page.tables) +
      '\n<div class="box">\n' + tables + '\n</div>' +
      ignored(page.ignored) + '\n';
  }

  // ---------------------------------------------------------------
  // A file page's cards' folds.

  // The cell drawing a branch, one kind per letter.
  function branchCell(branch) {
    var cells = Array.from(branch).map(function (kind) {
      return '<span class="bx" data-bx="' + kind + '"></span>';
    });
    return '<span class="branch" data-branch="" aria-hidden="true">' +
      cells.join('') + '</span>';
  }

  // Example: 1284 gives 1,284 times.
  function times(count) {
    var digits = String(count).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return digits + (count === 1 ? ' time' : ' times');
  }

  // A site row's count cells, 0 for a path never taken, else *.
  function countCells(counts) {
    return counts.map(function (count) {
      var never = count === 0;
      return '<span class="' + (never ? 'count never' : 'count') +
        '" data-count="" data-hover="' + times(count) + '">' +
        (never ? '0' : '*') + '</span>';
    }).join('');
  }

  // A fold row's cells, each [text, mark, hover].
  function valueCells(cells) {
    return cells.map(function (cell) {
      var attrs = 'class="cell" data-cell=""';
      if (cell[1] !== null) { attrs += ' data-mark="' + esc(cell[1]) + '"'; }
      if (cell[2] !== null) { attrs += ' data-hover="' + esc(cell[2]) + '"'; }
      return '<span ' + attrs + '>' + esc(cell[0]) + '</span>';
    }).join('');
  }

  // The attribute marking each kind of fold row, and the class and
  // attribute of its label's span.
  var KINDS = {
    site: ['', 'operator" data-operator="'],
    subtree: [' data-subtree=""', 'operator" data-operator="'],
    operand: [' data-operand=""', 'text" data-text="'],
    arm: [' data-arm=""', 'arm" data-label="'],
    leaves: [' data-leaves=""', 'arm" data-label="']
  };

  // The attribute name="line,column,line,column" of at; none for null.
  function atAttr(at, name) {
    return at ? ' ' + name + '="' + at.join(',') + '"' : '';
  }

  // One fold row.
  function foldRow(row) {
    var kind = KINDS[row.kind];
    var lead = row.branch === '' ? '' : branchCell(row.branch);
    var cells = row.counts ? countCells(row.counts) : valueCells(row.cells);
    var attrs = kind[0] + atAttr(row.at, 'data-at') +
      atAttr(row.else, 'data-else');
    return '<div class="row"' + attrs + '>' + lead + '<span class="' +
      kind[1] + '">' + painted(row.label) + '</span>' + cells + '</div>';
  }

  // ---------------------------------------------------------------
  // A file page's cards.

  // The class each of a card row's cells adds after pcell.
  var CELLS = ['', ' not-taken', ' was-taken'];

  // A card row: attrs, lead, its label, then a span per cell.
  function cardRow(attrs, label, cells, lead) {
    var spans = cells.map(function (cell, i) {
      var none = CELLS[i] === ' not-taken' && cell === '0' ? ' none' : '';
      return '<span class="pcell' + CELLS[i] + none + '">' + cell + '</span>';
    });
    return '<div ' + attrs + '>' + (lead || '') +
      '<span class="plabel">' + label + '</span>' + spans.join('') + '</div>';
  }

  // How many times a method was called, after its name; none when not
  // known.
  function callCount(calls) {
    if (calls === null) { return ''; }
    var css = calls === 0 ? 'call-count never' : 'call-count';
    return '<span class="' + css + '">&times;' + calls + '</span>';
  }

  // One row of a card, then its fold, if it has one.
  function statementRow(row) {
    var count = row.taken;
    var counts = count === null ? ['?', '?'] :
      [String(row.paths - count), String(count)];
    var cells = [painted(row.top)].concat(counts);
    var css = row.site ? 'prow site' : 'prow';
    var attrs = 'class="' + css + '" data-line="' +
      parseInt(row.at.match(/\d+/)[0], 10) + '"';
    var fold = row.fold ? row.fold.map(foldRow).join('') : null;
    var lead = fold === null ? '' :
      '<button type="button" class="fold-arrow" aria-expanded="false"' +
      ' aria-label="Paths of ' + row.at + '"></button>';
    var folded = fold === null ? '' :
      '<div class="fold" data-site="' + row.site + '" hidden="hidden">' +
      '<div class="site" data-site="">' + fold + '</div></div>';
    return cardRow(attrs, row.at, cells, lead) + folded;
  }

  // A card's HTML: its title row, its columns row, then its rows.
  function cardHtml(card) {
    var title = card.title;
    var label = esc(title.name) + callCount(title.calls);
    var head = cardRow('class="prow calls" data-line="' + card.first + '"',
      label, ['*' + title.ways, String(title.notTaken), String(title.taken)]) +
      cardRow('class="prow columns"', 'line:col',
        ['', 'not taken', 'taken']);
    var grid = card.top ? 'pathgrid statements top-level' : 'pathgrid statements';
    var attrs = 'id="paths-' + card.first + '" data-first="' + card.first +
      '" data-col="' + card.column + '" data-last="' + card.last +
      '" data-status="' + card.status + '" hidden="hidden"';
    return '<div class="' + grid + '" ' + attrs + '>' + head +
      card.rows.map(statementRow).join('') + '</div>';
  }

  // ---------------------------------------------------------------
  // A file page's listing and nav.

  // The first lines of the cards of status, in line order.
  function firsts(cards, status) {
    return cards.filter(function (card) { return card.status === status; })
      .map(function (card) { return card.first; })
      .sort(function (a, b) { return a - b; });
  }

  // Each status's arrows, gaps first, and how a label names it.
  var STATUSES = [['gaps', 'with gaps'], ['covered', 'covered']];

  // The header's row of jumps, to each card with gaps.
  function jumps(cards) {
    var links = firsts(cards, 'gaps').map(function (first) {
      return '<a class="jump" data-status="gaps" href="#L' + first + '">' +
        first + '</a>';
    });
    var empty = links.length === 0 ? ' data-empty=""' : '';
    return '<nav class="jumps" aria-label="Cards"><div class="jump-list"' +
      empty + '><span class="jump-label">Gaps</span>' + links.join('') +
      '</div></nav>';
  }

  // The gutter of a row of numbers: by each card's first line, an
  // arrow to the card of its status before it, and one after.
  function navCell(numbers, cards) {
    var links = [];
    STATUSES.forEach(function (named) {
      var status = named[0];
      var lines = firsts(cards, status);
      lines.filter(function (first) { return numbers.indexOf(first) >= 0; })
        .forEach(function (first) {
          var i = lines.indexOf(first);
          var arrow = function (way, word, line) {
            return '<a data-' + way + '="" data-status="' + status +
              '" href="#L' + line + '" aria-label="' + word + ' card ' +
              named[1] + ', line ' + line + '"></a>';
          };
          links.push(arrow('prev', 'Previous',
            lines[(i - 1 + lines.length) % lines.length]));
          links.push(arrow('next', 'Next', lines[(i + 1) % lines.length]));
        });
    });
    return '<span class="nav" data-nav="">' + links.join('') + '</span>';
  }

  // True when card holds line.
  function holds(card, line) { return card.first <= line && line <= card.last; }

  // The attributes of a line's code: in a method, its innermost one's
  // status and def's column, marked as its def line or last line.
  function srcAttributes(methods, number, text) {
    var holders = methods.filter(function (card) { return holds(card, number); });
    if (holders.length === 0) { return 'class="src"'; }
    var inner = holders.reduce(function (best, card) {
      return card.first > best.first ? card : best;
    });
    var css = ['src', 'in-method'];
    if (methods.some(function (card) { return card.first === number; })) {
      css.push('def-line');
    }
    if (methods.some(function (card) { return card.last === number; })) {
      css.push('method-end');
    }
    var style = '--def-col: ' + inner.column;
    if (inner.first === number) {
      style += '; --def-end: ' + Array.from(text).length;
    }
    return 'class="' + css.join(' ') + '" data-method-status="' +
      inner.status + '" style="' + style + '"';
  }

  // One line's number, a def's marked to open its method's card.
  function lineNumber(number, methods) {
    var card = methods.filter(function (each) { return each.first === number; })[0];
    var css = card
      ? 'class="lineno mdef" data-status="' + card.status + '" aria-expanded="false"'
      : 'class="lineno"';
    return '<span ' + css + ' id="L' + number + '" data-line="' + number +
      '">' + number + '</span>';
  }

  // One line's code, coloured.
  function code(line, number, methods) {
    return '<span ' + srcAttributes(methods, number, line.text) +
      ' data-src="">' + painted(line) + '</span>';
  }

  // The source listing: a row per line, but one row over all the
  // lines of a site outside every method.
  function listing(lines, cards) {
    var methods = cards.filter(function (card) { return !card.top; });
    var tops = {};
    cards.forEach(function (card) { if (card.top) { tops[card.first] = card; } });
    var loose = function (line) {
      return !methods.some(function (card) { return holds(card, line); });
    };
    var rows = [];
    lines.forEach(function (line, index) {
      var number = index + 1;
      var span = line.span;
      var key = span && loose(span[0]) ? 'span ' + span[0] + '-' + span[1] : number;
      var last = rows[rows.length - 1];
      if (last && last.key === key) {
        last.numbers.push(number);
      } else {
        rows.push({ key: key, span: typeof key === 'string', numbers: [number] });
      }
    });
    var body = rows.map(function (row) {
      if (!row.span) {
        var number = row.numbers[0];
        var line = lines[number - 1];
        var folded = methods.some(function (card) {
          return card.first + 1 <= number && number <= card.last;
        });
        return '<div class="' + (folded ? 'line method-folded' : 'line') + '">' +
          navCell([number], cards) + lineNumber(number, methods) +
          code(line, number, methods) + '</div>';
      }
      var first = row.numbers[0];
      var top = tops[first];
      var sites = top ? top.sites : 0;
      var count = sites < 2 ? '' :
        '<span class="site-count" data-site-count="">' + sites + '</span>';
      var spans = row.numbers.map(function (n) { return lineNumber(n, []); }).join('');
      var status = top ? top.status : (lines[first - 1].status || '');
      var button = '<button type="button" class="lnum loose" data-status="' +
        status + '" aria-expanded="false" aria-controls="paths-' + first +
        '">' + count + spans + '</button>';
      var srcs = row.numbers.map(function (n) {
        return code(lines[n - 1], n, []);
      }).join('');
      return '<div class="block">' + navCell(row.numbers, cards) + button +
        '<div class="srcs">' + srcs + '</div></div>';
    });
    return '<div class="code">\n' + body.join('\n') + '\n</div>';
  }

  // A file page's <main>.
  function filePage(page) {
    var path = esc(page.path);
    var index = '../'.repeat(page.path.split('/').length) + 'index.html';
    var rail = page.cards.map(cardHtml).join('\n');
    return '\n<header class="head" data-head="">\n' +
      '<div class="top"><p class="title"><a data-index="" href="' + index +
      '">Path coverage</a></p><h1 class="path"><a data-row="" href="' +
      index + '#row-' + path + '">' + path + '</a></h1>' +
      '<button type="button" class="theme" aria-label="Light or dark">' +
      '</button></div>\n' + jumps(page.cards) + '\n</header>\n' +
      '<div class="box">\n<div class="rail">\n' + rail + '\n</div>\n' +
      listing(page.lines, page.cards) + '\n' +
      '<div class="divider" role="separator" aria-orientation="vertical"' +
      ' title="Drag to share the width between paths and code"></div>\n' +
      '</div>\n';
  }

  var main = document.querySelector('main.page');
  if (data.page === 'index') {
    document.title = 'Path coverage';
    main.innerHTML = indexPage(data);
  } else {
    document.title = data.path + ' · Path coverage';
    main.innerHTML = filePage(data);
  }
}());
