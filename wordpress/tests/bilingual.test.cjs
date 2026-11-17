const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../tmp/wordpress-qa/node_modules/jsdom');
const Engine = require('../../tmp/wordpress-qa/node_modules/php-parser');
const catalog = JSON.parse(fs.readFileSync('wordpress/prc-bilingual/content/form-en.json','utf8'));
const script = fs.readFileSync('wordpress/prc-bilingual/form.js','utf8');

test('bilingual PHP parses and content has six unique draft pages with complete SEO', () => {
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-bilingual/prc-bilingual.php','utf8'));
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
