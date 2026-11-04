// Switches the index page's tabs: a click on a tab selects it and
// shows the table it controls, hiding every other tab's table.
(function () {
  var tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (other) {
        var selected = other === tab;
        other.setAttribute('aria-selected', selected ? 'true' : 'false');
        var table = document.getElementById(other.getAttribute('aria-controls'));
        table.hidden = !selected;
      });
    });
  });
})();
