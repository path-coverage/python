// Sorts the files table by the clicked column's data-sort values;
// a second click on the same column reverses the order. A cell
// with an empty data-sort, one with no value such as a -, stays
// last in both orders, so either end of the values can be first.
(function () {
  var table = document.getElementById('files');
  var body = table.tBodies[0];
  var state = { column: -1, ascending: true };

  table.querySelectorAll('thead button').forEach(function (button) {
    button.addEventListener('click', function () {
      var column = Number(button.dataset.column);
      var numeric = button.dataset.type === 'number';
      state.ascending = state.column === column ? !state.ascending : true;
      state.column = column;
      var rows = Array.from(body.rows);
      rows.sort(function (a, b) {
        var x = a.cells[column].dataset.sort;
        var y = b.cells[column].dataset.sort;
        if (x === '' || y === '') { return (x === '') - (y === ''); }
        var order = numeric ? Number(x) - Number(y) : x.localeCompare(y);
        return state.ascending ? order : -order;
      });
      rows.forEach(function (row) { body.appendChild(row); });
      table.querySelectorAll('thead th').forEach(function (th, i) {
        var sort = state.ascending ? 'ascending' : 'descending';
        th.setAttribute('aria-sort', i === column ? sort : 'none');
      });
    });
  });
})();
