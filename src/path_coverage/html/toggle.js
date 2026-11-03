// Opens and closes the tree a line-number button names in its
// aria-controls, keeping aria-expanded in step.
(function () {
  document.querySelectorAll('button[aria-controls]').forEach(function (button) {
    button.addEventListener('click', function () {
      var tree = document.getElementById(button.getAttribute('aria-controls'));
      var open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', open ? 'false' : 'true');
      tree.hidden = open;
    });
  });
})();
