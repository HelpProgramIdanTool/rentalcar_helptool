const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../tmp/wordpress-qa/node_modules/jsdom');
const Engine = require('../../tmp/wordpress-qa/node_modules/php-parser');
const code = fs.readFileSync('wordpress/prc-submit-guard/submit-guard.js','utf8');
function setup(validate) {
  const dom = new JSDOM('<form id="prcRequestForm"><input required name="email" value="test@example.test"><button type="submit">SEND</button><button type="submit" disabled>DISABLED</button></form>', {runScripts:'outside-only'});
  const form = dom.window.document.querySelector('form');
  if (validate) form.addEventListener('submit', validate);
  dom.window.eval(code);
  dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  return {dom, form, submit: () => form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}))};
}
test('plugin PHP parses', () => {
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-submit-guard/prc-submit-guard.php','utf8'));
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/prc-submit-guard/request-dedup.php','utf8'));
  new Engine({parser:{suppressErrors:false}}).parseCode(fs.readFileSync('wordpress/tests/request_dedup.integration.php','utf8'));
});
test('one accepted submission, two repeats blocked; data preserved', () => {
  const {dom,form,submit} = setup();
  assert.equal(submit(),true);
  assert.equal(form.querySelector('button').disabled,true);
  assert.equal(submit(),false);
  assert.equal(submit(),false);
  assert.equal(new dom.window.FormData(form).get('email'),'test@example.test');
  dom.window.close();
});
test('validation failure allows a corrected retry', () => {
  let invalid=true;
  const {dom,form,submit} = setup(e => {if (invalid) e.preventDefault();});
  assert.equal(submit(),false);
  assert.equal(form.querySelector('button').disabled,false);
  invalid=false;
  assert.equal(submit(),true);
  assert.equal(submit(),false);
  dom.window.close();
});
test('native invalid data does not lock form', () => {
  const {dom,form,submit} = setup();
  form.querySelector('input').value='';
  submit();
  assert.equal(form.querySelector('button').disabled,false);
  form.querySelector('input').value='fixed@example.test';
  assert.equal(submit(),true);
  assert.equal(submit(),false);
  dom.window.close();
});
test('back navigation unlocks only buttons locked by guard', () => {
  const {dom,form,submit} = setup();
  submit();
  dom.window.dispatchEvent(new dom.window.Event('pageshow'));
  assert.equal(form.querySelectorAll('button')[0].disabled,false);
  assert.equal(form.querySelectorAll('button')[1].disabled,true);
  assert.equal(form.hasAttribute('aria-busy'),false);
  assert.equal(submit(),true);
  dom.window.close();
});
test('loading guard twice does not block first submission', () => {
  const {dom,submit} = setup();
  dom.window.eval(code);
  dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
  assert.equal(submit(),true);
  assert.equal(submit(),false);
  dom.window.close();
});
