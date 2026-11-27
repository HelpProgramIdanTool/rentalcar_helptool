const {JSDOM}=require('../../tmp/wordpress-qa/node_modules/jsdom');
const fs=require('fs'),assert=require('node:assert/strict');
const Engine=require('../../tmp/wordpress-qa/node_modules/php-parser');
const php=new Engine({parser:{php7:true},ast:{withPositions:true}});
for(const plugin of ['prc-bilingual','trip-rental-page']){
 for(const extension of ['js','php']){
  const name=`driver-requirements.${extension}`;
  assert.equal(fs.readFileSync(`wordpress/${plugin}/${name}`,'utf8'),fs.readFileSync(`wordpress/${name}`,'utf8'));
 }
 php.parseCode(fs.readFileSync(`wordpress/${plugin}/driver-requirements.php`,'utf8'));
}
const script=fs.readFileSync('wordpress/driver-requirements.js','utf8');
for(const lang of ['he','en'])for(const radio of [true,false]){
 const old=radio?'<div class="prc-field"><label>OLD</label><label><input type="radio" name="driver_age" value="כן" required>YES</label><label><input type="radio" name="driver_age" value="לא">NO</label></div>':'<label>OLD<select name="age"><option>כן</option><option>לא</option></select></label>';
 const dom=new JSDOM(`<div lang="${lang}"><form>${old}</form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
 const doc=dom.window.document,toggle=doc.querySelector('input[type=checkbox]'),payload=doc.querySelector('[name=driver_requirements]');
 assert.deepEqual(JSON.parse(payload.value),{exception:false,drivers:[]});
 assert.equal(doc.querySelectorAll('[name=driver_requirements]').length,1);
 toggle.checked=true;toggle.dispatchEvent(new dom.window.Event('change'));
 const age=doc.querySelector('[data-age]'),months=doc.querySelector('[data-months]');
 assert.equal(age.required,true);age.value='22';months.value='4';months.dispatchEvent(new dom.window.Event('input'));
 assert.deepEqual(JSON.parse(payload.value),{exception:true,drivers:[{age:22,license_months:4}]});
 if(radio)assert.equal(doc.querySelector('[name=driver_age]:checked').value,'לא');
 toggle.checked=false;toggle.dispatchEvent(new dom.window.Event('change'));
 assert.equal(age.required,false);assert.equal(JSON.parse(payload.value).drivers.length,0);
 assert.equal(doc.querySelector('section').textContent.includes(lang==='en'?'Licence experience':'ותק רישיון'),true);
 dom.window.close();
}
console.log('Public driver editor: Hebrew/English, radios/select, numeric values and declaration toggles passed.');
