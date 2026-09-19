document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('#result_list tbody tr').forEach(row => {
    const link = row.querySelector('th.field-customer_label a');
    if (!link) return;
    row.style.cursor = 'pointer';
    row.addEventListener('click', event => {
      if (event.target.closest('a, input, button, select, label') || window.getSelection().toString()) return;
      window.location.href = link.href;
    });
  });
});
