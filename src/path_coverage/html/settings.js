// The report's settings, eg its theme. Each is carried by
// every link to another page of the report, as ?name=, since some
// browsers keep nothing shared between a report's local files, and
// is also kept in the browser where it can be, for a page opened
// afresh.
window.pathCoverageSettings = (function () {
  // The value of setting name the link that opened this page
  // carried, else the one last kept, when it is one of allowed;
  // else null.
  function given(name, allowed) {
    var match = new RegExp('[?&]' + name + '=([a-z]+)').exec(window.location.search);
    if (match && allowed.indexOf(match[1]) >= 0) { return match[1]; }
    try {
      var kept = window.localStorage.getItem('path_coverage.' + name);
      return allowed.indexOf(kept) >= 0 ? kept : null;
    } catch (e) { return null; }
  }

  // Keeps value as setting name's, where the browser allows it.
  function keep(name, value) {
    try { window.localStorage.setItem('path_coverage.' + name, value); } catch (e) { /* carried by links only */ }
  }

  // href, a link to another page of the report, with its ?name=
  // set to value, before any #fragment, its other ?settings kept.
  function carrying(href, name, value) {
    var hash = href.indexOf('#');
    var fragment = hash < 0 ? '' : href.slice(hash);
    var rest = hash < 0 ? href : href.slice(0, hash);
    var query = rest.indexOf('?');
    var page = query < 0 ? rest : rest.slice(0, query);
    var settings = query < 0 ? [] : rest.slice(query + 1).split('&').filter(function (pair) {
      return pair && pair.split('=')[0] !== name;
    });
    settings.push(name + '=' + value);
    return page + '?' + settings.join('&') + fragment;
  }

  // Makes every link to another of the report's pages carry value
  // as setting name's.
  function carry(name, value) {
    document.querySelectorAll('a[href]').forEach(function (link) {
      var href = link.getAttribute('href');
      if (/^[a-z]+:|^#/.test(href) || !/\.html(\?|#|$)/.test(href)) { return; }
      link.setAttribute('href', carrying(href, name, value));
    });
  }

  return { given: given, keep: keep, carry: carry };
})();
