// Switches the page between light and dark as the title bar's theme
// button is pressed: the page's html element names the theme, and
// the page's CSS draws it. The theme is a setting, carried from page
// to page as settings.js has it; a page with none opens dark.
(function () {
  var settings = window.pathCoverageSettings;
  var button = document.querySelector('button.theme');
  if (!button) { return; }

  // Names theme on the html element, labels the button with the
  // theme it switches to, and makes every link carry theme.
  function show(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var other = theme === 'dark' ? 'light' : 'dark';
    button.textContent = String.fromCharCode(theme === 'dark' ? 0x2600 : 0x263E);
    button.setAttribute('aria-label', 'Switch to ' + other);
    button.title = 'Switch to ' + other;
    settings.carry('theme', theme);
  }

  show(settings.given('theme', ['light', 'dark']) || 'dark');
  button.addEventListener('click', function () {
    var theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    show(theme);
    settings.keep('theme', theme);
  });
})();
