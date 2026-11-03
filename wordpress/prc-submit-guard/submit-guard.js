(function () {
  'use strict';
  function init() {
    var form = document.getElementById('prcRequestForm');
    if (!form || form.dataset.prcSubmitGuard === '1') return;
    form.dataset.prcSubmitGuard = '1';
    var sending = false;
    var changedButtons = [];
    var previousBusy = null;
    form.addEventListener('submit', function (event) {
      if (sending) {
        event.preventDefault();
        return;
      }
      // The existing plugin's listener runs first and validates the last step.
      // A rejected submission must never lock the form.
      if (event.defaultPrevented || !form.checkValidity()) return;
      sending = true;
      previousBusy = form.getAttribute('aria-busy');
      form.setAttribute('aria-busy', 'true');
      changedButtons = Array.prototype.filter.call(
        form.querySelectorAll('button[type="submit"], input[type="submit"]'),
        function (button) { return !button.disabled; }
      );
      changedButtons.forEach(function (button) { button.disabled = true; });
    });
    // Browsers can restore a disabled form from their back/forward cache.
    window.addEventListener('pageshow', function () {
      if (!sending) return;
      sending = false;
      changedButtons.forEach(function (button) { button.disabled = false; });
      changedButtons = [];
      if (previousBusy === null) form.removeAttribute('aria-busy');
      else form.setAttribute('aria-busy', previousBusy);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
