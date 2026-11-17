(function () {
  'use strict';
  function setup() {
    if (!document.querySelector('.prc-form-wrap[lang="en"]')) return;
    ['pickup','dropoff'].forEach(side => {
      const get = suffix => document.getElementById('prc_'+side+'_'+suffix);
      const display=get('date_display'), native=get('date_native'), hidden=get('date');
      if (display && native && hidden) {
        function showDate() {
          const match=native.value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
          display.value=match ? `${match[3]}.${match[2]}.${match[1]}` : '';
          if (match) display.setCustomValidity('');
        }
        native.addEventListener('change',showDate);
        display.addEventListener('input', () => {
          const match=display.value.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
          const date=match ? new Date(Date.UTC(+match[3],+match[2]-1,+match[1])) : null;
          const valid=!!date && date.getUTCFullYear()===+match[3] && date.getUTCMonth()===+match[2]-1 && date.getUTCDate()===+match[1];
          if (!valid) {
            hidden.value=''; native.value='';
            display.setCustomValidity(display.value ? 'Enter a valid date as DD.MM.YYYY.' : 'Choose a date.');
            return;
          }
          const iso=`${match[3]}-${match[2]}-${match[1]}`;
          native.value=iso;
          hidden.value=`${match[1]}/${match[2]}/${match[3]}`;
          display.setCustomValidity('');
          native.dispatchEvent(new Event('change',{bubbles:true}));
          hidden.dispatchEvent(new Event('change',{bubbles:true}));
          showDate();
        });
        showDate();
      }
      const select=get('half_hour'), value=get('time'), oldDisplay=get('time_display');
      if (select && value) {
        const label=document.querySelector('label[for="prc_'+side+'_time_display"]');
        if (label) label.htmlFor=select.id;
        select.value=/^(?:[01]\d|2[0-3]):(?:00|30)$/.test(value.value) ? value.value : '';
        select.addEventListener('change', () => {
          value.value=select.value;
          if (oldDisplay) { oldDisplay.value=select.value; oldDisplay.setCustomValidity(''); }
          const parts=select.value.split(':');
          if (get('hour')) get('hour').value=parts[0] || '';
          if (get('minute')) get('minute').value=parts[1] || '';
          value.dispatchEvent(new Event('change',{bubbles:true}));
        });
      }
    });
  }
  // Run after the existing handler and date compatibility plugin finish initializing.
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', () => setTimeout(setup,0));
  else setTimeout(setup,0);
}());
