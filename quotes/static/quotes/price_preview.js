(() => {
  const status = document.getElementById('price-preview-status');
  if (!status) return;
  const form = status.closest('form');
  const fields = new Set(['suppliers','sub_agent','driver_count','extra_choices','child_seat_quantity','young_driver_quantity','cross_border_requested']);
  const relevant = name => name.startsWith('pickup_') || name.startsWith('return_') || fields.has(name);
  const labels = new Map();
  form.querySelectorAll('input[name="vehicle_groups"]').forEach(input => {
    const span = document.createElement('span');
    span.className = 'vehicle-price';
    input.closest('label').append(span);
    labels.set(input.value, span);
  });
  let timer, controller, version = 0;
  const clear = text => labels.forEach(span => { span.textContent = text; span.title = ''; });
  function schedule() {
    clearTimeout(timer);
    controller?.abort();
    const current = ++version;
    clear(' (…)');
    status.textContent = 'Обновляю цены…';
    timer = setTimeout(() => update(current), 450);
  }
  async function update(current) {
    controller = new AbortController();
    const payload = new FormData();
    for (const [name, value] of new FormData(form)) {
      if (relevant(name) || name === 'csrfmiddlewaretoken') payload.append(name, value);
    }
    try {
      const response = await fetch(status.dataset.url, {method:'POST',body:payload,signal:controller.signal});
      const result = await response.json();
      if (current !== version) return;
      clear('');
      if (!response.ok) {
        const errors = Object.values(result.errors || {}).flat().map(error => error.message);
        status.textContent = errors.length ? 'Для расчёта: ' + [...new Set(errors)].join(' ') : 'Не удалось рассчитать цены.';
        return;
      }
      labels.forEach((span, id) => {
        const price = result.prices[id];
        if (!price) return;
        span.textContent = price.available ? ` (${price.total} ${price.currency})` : ' (нет расчёта)';
        span.title = price.available ? 'Итого за весь срок с выбранными добавками, до ручной доплаты.' : price.reason;
      });
      status.textContent = `Цены за весь срок (${result.days} дн.), с выбранными добавками. Ручные доплаты — на следующем шаге.`;
    } catch (error) {
      if (current !== version || error.name === 'AbortError') return;
      clear('');
      status.textContent = 'Не удалось обновить цены. Измените поле, чтобы повторить расчёт.';
    }
  }
  ['input','change'].forEach(event => form.addEventListener(event, e => {
    if (relevant(e.target.name || '')) schedule();
  }));
  form.addEventListener('pricingchange', schedule);
  schedule();
})();
