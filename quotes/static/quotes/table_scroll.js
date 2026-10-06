(() => {
  document.querySelectorAll('.table-scroll').forEach(bottom => {
  const table = bottom.querySelector('table');
  if (!table) return;
  const controls = document.createElement('div');
  controls.className = 'table-scroll-controls';
  const label = document.createElement('label');
  label.textContent = 'Сдвинуть таблицу';
  const slider = document.createElement('input');
  slider.type = 'range'; slider.min = '0'; slider.step = '1'; slider.value = '0';
  slider.setAttribute('aria-label', 'Горизонтальная прокрутка таблицы');
  const left = document.createElement('button');
  const right = document.createElement('button');
  left.type = right.type = 'button'; left.textContent = '←'; right.textContent = '→';
  left.setAttribute('aria-label', 'Прокрутить таблицу влево');
  right.setAttribute('aria-label', 'Прокрутить таблицу вправо');
  label.append(slider); controls.append(left, label, right); bottom.before(controls);
  function sync() {
    slider.value = String(bottom.scrollLeft);
    left.disabled = bottom.scrollLeft <= 0;
    right.disabled = bottom.scrollLeft >= Number(slider.max) - 1;
  }
  function resize() {
    slider.max = String(Math.max(0, bottom.scrollWidth - bottom.clientWidth));
    slider.disabled = Number(slider.max) === 0;
    controls.hidden = slider.disabled;
    sync();
  }
  slider.addEventListener('input', () => { bottom.scrollLeft = Number(slider.value); sync(); });
  left.addEventListener('click', () => { bottom.scrollLeft -= bottom.clientWidth / 2; sync(); });
  right.addEventListener('click', () => { bottom.scrollLeft += bottom.clientWidth / 2; sync(); });
  bottom.addEventListener('scroll', sync, {passive: true});
  window.addEventListener('resize', resize);
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(resize);
    observer.observe(bottom);
    observer.observe(table);
  }
  resize();
  if (document.fonts?.ready) document.fonts.ready.then(resize);
  });
})();
