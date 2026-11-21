const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('../tmp/wordpress-qa/node_modules/jsdom');

test('local mode filters suppliers and cities; ordinary switch preserves customer and route data',()=>{
 const html=`<form><input name="customer" value="KEEP-CUSTOMER"><select id="id_local_rental_branch"><option value="">Ordinary</option><option value="9">Local</option></select><select id="id_rental_country"><option>PL</option><option>CZ</option></select><label><input id="id_cross_border_requested" type="checkbox"> NORMAL BORDER</label><p id="local-mode-help"></p><button id="ordinary-rental-mode" type="button">Ordinary</button><label><input type="checkbox" name="suppliers" value="1" checked></label><label><input type="checkbox" name="suppliers" value="2" checked></label><div class="vehicle-picker"><div class="vehicle-section"><div class="vehicle-supplier"><label><input type="checkbox" data-supplier-id="1"></label></div><div class="vehicle-supplier"><label><input type="checkbox" data-supplier-id="2" checked></label></div></div></div><select id="id_pickup_city"><option>Warsaw</option><option>Prague</option></select><select id="id_return_city"><option>Warsaw</option><option>Prague</option></select></form><script type="application/json" id="local-rental-modes">{"9":{"supplier":"1","country":"CZ","city":"Prague","cities":["Prague"],"help":"TEST-HELP","cross_border_label":"TEST-CZECH-BORDER"}}</script>`;
 const dom=new JSDOM(html,{runScripts:'outside-only'}),d=dom.window.document;
 dom.window.eval(fs.readFileSync('quotes/static/quotes/local_rental_mode.js','utf8'));
 const mode=d.getElementById('id_local_rental_branch');mode.value='9';mode.dispatchEvent(new dom.window.Event('change',{bubbles:true}));
 assert.equal(d.getElementById('id_rental_country').value,'CZ');
 assert.equal(d.getElementById('id_pickup_city').value,'Prague');
 assert.equal(d.querySelector('input[name="suppliers"][value="2"]').disabled,true);
 assert.equal(d.getElementById('id_pickup_city').options[0].disabled,true);
 assert.match(d.getElementById('id_cross_border_requested').closest('label').textContent,/TEST-CZECH-BORDER/);
 d.getElementById('ordinary-rental-mode').click();
 assert.equal(mode.value,'');assert.equal(d.getElementById('id_rental_country').value,'PL');
 assert.equal(d.getElementById('id_pickup_city').value,'Prague');
 assert.equal(d.querySelector('[name="customer"]').value,'KEEP-CUSTOMER');
 assert.equal(d.getElementById('id_pickup_city').options[0].disabled,false);
 assert.equal(d.querySelector('input[name="suppliers"][value="2"]').disabled,false);
 dom.window.close();
});
