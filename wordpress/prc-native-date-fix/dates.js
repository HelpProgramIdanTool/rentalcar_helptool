(function () {
  'use strict';
  function setup() {
    ['pickup', 'dropoff'].forEach(function (prefix) {
      var native = document.getElementById('prc_' + prefix + '_date_native');
      var display = document.getElementById('prc_' + prefix + '_date_display');
      if (!native || !display || native.type !== 'date') return;
      native.removeAttribute('aria-hidden');
      native.removeAttribute('tabindex');
      native.required = true;
      var label = document.querySelector('label[for="' + display.id + '"]');
      if (label) label.htmlFor = native.id;
      // Retain the old display node: the form's existing validation and sync code uses it.
      display.closest('.prc-calendar-control').classList.add('prc-direct-date');
      native.addEventListener('input', function () {
        native.dispatchEvent(new Event('change', { bubbles: true }));
      });
      native.addEventListener('focus', function () {
        ['pickup', 'dropoff'].forEach(function (side) {
          var popover = document.getElementById('prc_' + side + '_time_popover');
          if (popover) popover.hidden = true;
        });
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
}());
