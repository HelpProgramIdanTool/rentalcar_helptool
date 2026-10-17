const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../tmp/wordpress-qa/node_modules/jsdom');
const Engine = require('../../tmp/wordpress-qa/node_modules/php-parser');

test('PHP syntax is valid', () => {
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-native-date-fix/prc-native-date-fix.php','utf8'));
});

test('native inputs are accessible, preserve date limits and update existing submitted values', () => {
  const html = ['pickup','dropoff'].map(p => `<label for="prc_${p}_date_display">TEST-DATE</label><div class="prc-calendar-control"><input id="prc_${p}_date_display" readonly><button class="prc-picker-icon"></button><input id="prc_${p}_date_native" type="date" min="2026-10-17" tabindex="-1" aria-hidden="true"><input id="prc_${p}_date" type="hidden" name="${p}_date"></div><div id="prc_${p}_time_popover"></div>`).join('');
  const dom = new JSDOM(html,{runScripts:'outside-only'});
  const doc = dom.window.document;
  ['pickup','dropoff'].forEach(p => {
    doc.getElementById(`prc_${p}_date_native`).addEventListener('change', e => {
      const [y,m,d] = e.target.value.split('-');
      doc.getElementById(`prc_${p}_date`).value = `${d}/${m}/${y}`;
    });
  });
  dom.window.eval(fs.readFileSync('wordpress/prc-native-date-fix/dates.js','utf8'));
  doc.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  ['pickup','dropoff'].forEach(p => {
    const native = doc.getElementById(`prc_${p}_date_native`);
    assert.equal(doc.querySelector(`label[for="${native.id}"]`).textContent,'TEST-DATE');
    assert.equal(native.hasAttribute('aria-hidden'),false);
    assert.equal(native.required,true);
    assert.equal(native.min,'2026-10-17');
    native.value = '2026-11-20';
    native.dispatchEvent(new dom.window.Event('input'));
    assert.equal(doc.getElementById(`prc_${p}_date`).value,'20/11/2026');
    native.focus();
    assert.equal(doc.getElementById('prc_pickup_time_popover').hidden,true);
    assert.equal(doc.getElementById('prc_dropoff_time_popover').hidden,true);
  });
});
