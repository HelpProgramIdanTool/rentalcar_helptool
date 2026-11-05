(function (root) {
  function normalize(value) {
    return String(value || '').toUpperCase()
      .replace(/\b(?:AUT|AUTO|AT)\b/g, 'AUTOMATIC')
      .replace(/\b(?:MAN|MT)\b/g, 'MANUAL')
      .replace(/[^A-Z0-9]+/g, ' ').trim();
  }
  function matchCategory(category, options, supplier, suppliersByGroup) {
    if (!supplier || !normalize(category)) return '';
    const wanted = normalize(category);
    const matches = Array.from(options).filter(option => {
      if (!option.value || String(suppliersByGroup[option.value]) !== String(supplier)) return false;
      const label = option.textContent || option.label || '';
      const detail = label.includes(' — ') ? label.split(' — ').slice(1).join(' — ') : label;
      const code = label.match(/\(([^()]*)\)\s*$/)?.[1];
      return [label, detail, detail.replace(/\s*\([^()]*\)\s*$/, ''), code]
        .some(value => normalize(value) === wanted);
    });
    return matches.length === 1 ? String(matches[0].value) : '';
  }
  const api = {matchCategory};
  root.BookingPaste = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
