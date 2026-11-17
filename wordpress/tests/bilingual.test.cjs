const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../tmp/wordpress-qa/node_modules/jsdom');
const Engine = require('../../tmp/wordpress-qa/node_modules/php-parser');
const catalog = JSON.parse(fs.readFileSync('wordpress/prc-bilingual/content/form-en.json','utf8'));
const script = fs.readFileSync('wordpress/prc-bilingual/form.js','utf8');
const pickers = fs.readFileSync('wordpress/prc-bilingual/pickers.js','utf8');

test('bilingual PHP parses and content has six unique draft pages with complete SEO', () => {
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-bilingual/prc-bilingual.php','utf8'));
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-bilingual/request-full-width.php','utf8'));
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-bilingual/stage-one.php','utf8'));
  const pages = JSON.parse(fs.readFileSync('wordpress/prc-bilingual/content/en-pages.json','utf8'));
  assert.equal(pages.length,6);
  assert.equal(new Set(pages.map(p=>p.slug)).size,6);
  for (const page of pages) {
    assert.ok(page.seo_title.length < 75);
    assert.ok(page.meta_description.length >= 70 && page.meta_description.length <= 165);
    assert.ok(page.focus_keyword && page.content);
    assert.doesNotMatch(page.content,/[\u0590-\u05ff]/);
  }
});

test('foundation pages have unique translation pairs and complete English content', () => {
  const stage=JSON.parse(fs.readFileSync('wordpress/prc-bilingual/content/stage-one.json','utf8'));
  assert.equal(new Set(stage.pairs.map(x=>x.he)).size,stage.pairs.length);
  assert.equal(new Set(stage.pairs.map(x=>x.en)).size,stage.pairs.length);
  for(const pair of stage.pairs) {
    assert.ok(stage.hebrew_pages.includes(pair.he));
    assert.ok(stage.english_pages.includes(pair.en));
  }
  for(const page of stage.menu) assert.ok(stage.publish_pages.includes(page.page));
  const pages=JSON.parse(fs.readFileSync('wordpress/prc-bilingual/content/foundation-pages.json','utf8'));
  assert.deepEqual(pages.map(x=>x.key),['guides','privacy']);
  for(const page of pages) {
    assert.ok(page.content && page.seo_title && page.meta_description.length<=165);
    assert.doesNotMatch(page.content,/[\u0590-\u05ff]/);
  }
});

test('all fourteen established vehicle categories have English labels', () => {
  const groups = ['רכב קטן','רכב סטנדרטי סדאן','רכב משפחתי / מנהלים גדול, סדאן',
    'רכב סטיישן','רכב היברידי','קראסאובר SUV קטן','קראסאובר SUV בינוני','קראסאובר SUV גדול',
    'רכב פרמיום סדאן','רכב פרמיום SUV קטן','רכב פרמיום SUV בינוני','רכב פרמיום SUV גדול',
    'רכב של 7 מקומות','רכב 8/9 מקומות'];
  for (const group of groups) assert.ok(catalog[group],group);
  for (const translation of Object.values(catalog)) assert.doesNotMatch(translation,/[\u0590-\u05ff]/);
});

function page(language='en') {
  const dom = new JSDOM(`<div class="prc-form-wrap" lang="${language}"><form id="prcRequestForm"><span id="message">לא חושב עדיין</span><input id="answer" name="driver_age" value="כן"><textarea>לא</textarea><select><option value="שדה תעופה">Airport</option></select></form></div>`,{runScripts:'outside-only'});
  dom.window.PRCFormEnglish=catalog;
  const alerts=[];
  dom.window.alert=value=>alerts.push(value);
  dom.window.eval(script);
  dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  return {dom,window:dom.window,document:dom.window.document,alerts};
}

test('dynamic messages translate while submitted values and customer notes stay intact', async () => {
  const {window,document}=page();
  assert.equal(document.querySelector('#message').textContent,'Not calculated yet');
  assert.equal(document.querySelector('#answer').value,'כן');
  assert.equal(document.querySelector('textarea').value,'לא');
  assert.equal(document.querySelector('select').value,'שדה תעופה');
  document.querySelector('#message').textContent='3 ימי שכירות';
  await new Promise(resolve=>window.setTimeout(resolve,0));
  assert.equal(document.querySelector('#message').textContent,'3 rental days');
  document.querySelector('#message').textContent='מועד החזרת הרכב חייב להיות לאחר מועד הקבלה.';
  await new Promise(resolve=>window.setTimeout(resolve,0));
  assert.equal(document.querySelector('#message').textContent,'Return must be after collection.');
});

test('English alerts and native validity messages use English', () => {
  const {window,document,alerts}=page();
  window.alert('נא לבחור לפחות קבוצת רכב אחת.');
  assert.deepEqual(alerts,['Choose at least one vehicle category.']);
  const input=document.querySelector('input');
  input.setCustomValidity('יש לבחור תאריך קבלה.');
  assert.equal(input.validationMessage,'Choose a collection date.');
});

test('Hebrew alerts, validity and form presentation remain Hebrew', () => {
  const {window,document,alerts}=page('he');
  window.alert('נא לבחור לפחות קבוצת רכב אחת.');
  assert.deepEqual(alerts,['נא לבחור לפחות קבוצת רכב אחת.']);
  const input=document.querySelector('input');
  input.setCustomValidity('יש לבחור תאריך קבלה.');
  assert.equal(input.validationMessage,'יש לבחור תאריך קבלה.');
  assert.equal(document.querySelector('#message').textContent,'לא חושב עדיין');
});

async function pickerPage() {
  const controls=['pickup','dropoff'].map(side=>`<label for="prc_${side}_time_display">Time</label><input id="prc_${side}_date_display"><input id="prc_${side}_date_native" type="date"><input id="prc_${side}_date"><input id="prc_${side}_time"><input id="prc_${side}_time_display"><select id="prc_${side}_half_hour" required><option value=""></option><option value="00:30">00:30</option><option value="23:30">23:30</option></select>`).join('');
  const dom=new JSDOM('<div class="prc-form-wrap" lang="en">'+controls+'</div>',{runScripts:'outside-only'});
  dom.window.eval(pickers);
  dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  await new Promise(resolve=>dom.window.setTimeout(resolve,10));
  return dom;
}

test('dot dates accept actual calendar days and keep original server date format', async () => {
  const dom=await pickerPage(),doc=dom.window.document;
  const display=doc.getElementById('prc_pickup_date_display');
  display.value='29.02.2028';
  display.dispatchEvent(new dom.window.Event('input'));
  assert.equal(doc.getElementById('prc_pickup_date_native').value,'2028-02-29');
  assert.equal(doc.getElementById('prc_pickup_date').value,'29/02/2028');
  display.value='29.02.2030';
  display.dispatchEvent(new dom.window.Event('input'));
  assert.equal(doc.getElementById('prc_pickup_date').value,'');
  assert.match(display.validationMessage,/valid date/);
  const native=doc.getElementById('prc_pickup_date_native');
  native.value='2030-12-23';
  native.dispatchEvent(new dom.window.Event('change'));
  assert.equal(display.value,'23.12.2030');
  assert.equal(display.validationMessage,'');
});

test('time choices pass exact 24-hour values to existing controls', async () => {
  const dom=await pickerPage(),doc=dom.window.document;
  for (const value of ['00:30','23:30']) {
    const select=doc.getElementById('prc_dropoff_half_hour');
    select.value=value;
    select.dispatchEvent(new dom.window.Event('change'));
    assert.equal(doc.getElementById('prc_dropoff_time').value,value);
    assert.equal(doc.getElementById('prc_dropoff_time_display').value,value);
  }
});
