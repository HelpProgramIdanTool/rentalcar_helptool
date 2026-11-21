(function () {
  'use strict';
  function mount() {
    document.querySelectorAll('.et-l--header .et_pb_menu, #main-header').forEach(function (header) {
      var target = header.querySelector('.et_pb_menu__wrap, .et_menu_container');
      var source = header.querySelector('.prc-language-menu .prc-language-switcher');
      if (!target || !source || target.querySelector('.prc-mobile-language-switcher')) return;
      var switcher = source.cloneNode(true);
      switcher.classList.add('prc-mobile-language-switcher');
      target.insertBefore(switcher, target.firstChild);
      header.classList.add('prc-mobile-languages-ready');
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
  window.addEventListener('load', mount);
}());
