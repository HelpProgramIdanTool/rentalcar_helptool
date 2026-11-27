/* Shared compact age/experience editor. Values refer to the pickup date. */
(function () {
  function init(root) {
    if (root.dataset.driverInitialized) return;
    root.dataset.driverInitialized = '1';
    const input = root.querySelector('input[type=hidden]');
    if (!input) return;
    const toggle = root.querySelector('[data-driver-exception]');
    const rows = root.querySelector('[data-driver-rows]');
    const add = root.querySelector('[data-driver-add]');
    let saved = {};
    try { saved = JSON.parse(input.value || '{}'); } catch (_) {}
    if (!saved || typeof saved !== 'object' || Array.isArray(saved)) saved = {};
    toggle.checked = saved.exception === true;
    function sync() {
      input.value = JSON.stringify({exception: toggle.checked, drivers: toggle.checked
        ? Array.from(rows.children).map(row => ({age: Number(row.querySelector('[data-age]').value),
            license_months: Number(row.querySelector('[data-months]').value)})) : []});
      input.dispatchEvent(new Event('change', {bubbles: true}));
    }
    function row(value = {}) {
      const box = document.createElement('div');
      box.className = 'driver-detail-row';
      for (const [key, label, max] of [['age', root.dataset.ageLabel, 100], ['months', root.dataset.monthsLabel, 1019]]) {
        const wrap = document.createElement('label'); wrap.textContent = label + ' ';
        const field = document.createElement('input'); field.type = 'number'; field.min = key === 'age' ? 16 : 0;
        field.max = max; field.step = 1; field.required = toggle.checked;
        field.dataset[key] = '';
        field.value = value[key === 'age' ? 'age' : 'license_months'] ?? '';
        field.addEventListener('input', sync); wrap.append(field); box.append(wrap);
      }
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×';
      remove.className = 'driver-remove'; remove.setAttribute('aria-label', root.dataset.removeLabel);
      remove.addEventListener('click', () => { box.remove(); sync(); }); box.append(remove); rows.append(box);
    }
    function display() {
      rows.hidden = add.hidden = !toggle.checked;
      if (toggle.checked && !rows.children.length) row();
      rows.querySelectorAll('input').forEach(field => field.required = toggle.checked);
    }
    (Array.isArray(saved.drivers) ? saved.drivers : []).forEach(row); display();
    toggle.addEventListener('change', () => { display(); sync(); });
    add.addEventListener('click', () => { if (rows.children.length < 9) { row(); sync(); } });
    // A new form makes an explicit declaration; old saved data remain untouched until editing.
    if (!input.value || input.value === '{}' || input.value === 'null') sync();
  }
  document.querySelectorAll('[data-driver-editor]').forEach(init);
  document.addEventListener('driverdetailsloaded', () => {
    document.querySelectorAll('[data-driver-editor]').forEach(root => {
      delete root.dataset.driverInitialized;
      // Replace controls to remove old listeners when an inquiry is imported.
      const copy = root.cloneNode(true); copy.querySelector('[data-driver-rows]').replaceChildren();
      root.replaceWith(copy); init(copy);
    });
  });
})();
