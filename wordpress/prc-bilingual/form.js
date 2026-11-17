(function () {
  'use strict';
  const catalog = window.PRCFormEnglish || {};
  function translate(value) {
    const key = String(value).replace(/\s+/g, ' ').trim();
    if (Object.prototype.hasOwnProperty.call(catalog, key)) return catalog[key];
    const days = String(value).match(/^(\d+)\s+ימי שכירות$/);
    return days ? days[1] + ' rental days' : value;
  }
  function englishForm() { return document.querySelector('.prc-form-wrap[lang="en"]'); }
  // Existing scripts create date messages after rendering. Keep their logic and translate presentation.
  function translateNode(node) {
    if (node.nodeType === 3) {
      if (node.parentElement?.closest('script,style,textarea,option')) return;
      const translated = translate(node.nodeValue);
      if (translated !== node.nodeValue) node.nodeValue = translated;
    } else if (node.nodeType === 1) {
      if (node.matches('script,style,textarea,option')) return;
      for (const child of Array.from(node.childNodes)) translateNode(child);
    }
  }
  const originalAlert = window.alert;
  window.alert = function (message) {
    return originalAlert.call(window, englishForm() ? translate(message) : message);
  };
  for (const prototype of [HTMLInputElement.prototype, HTMLSelectElement.prototype, HTMLTextAreaElement.prototype]) {
    const original = prototype.setCustomValidity;
    prototype.setCustomValidity = function (message) {
      return original.call(this, this.closest('.prc-form-wrap[lang="en"]') ? translate(message) : message);
    };
  }
  function ready() {
    const wrapper = englishForm();
    if (!wrapper) return;
    translateNode(wrapper);
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'characterData') translateNode(record.target);
        else for (const node of record.addedNodes) translateNode(node);
      }
    }).observe(wrapper, {subtree:true, childList:true, characterData:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
}());
