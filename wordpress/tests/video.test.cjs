const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { JSDOM } = require('../../tmp/wordpress-qa/node_modules/jsdom');
const Engine = require('../../tmp/wordpress-qa/node_modules/php-parser');

test('PHP parses without syntax errors', () => {
  new Engine({parser: {suppressErrors: false}}).parseCode(fs.readFileSync('wordpress/prc-page-speed/prc-page-speed.php', 'utf8'));
});

function page(src = 'https://www.youtube.com/embed/IBwvcUYDFio?feature=oembed') {
  const dom = new JSDOM(`<div class="prc-video"><a class="prc-video-link" aria-label="TEST-TITLE" href="https://www.youtube.com/watch?v=IBwvcUYDFio"><span>Play</span></a></div>`, {runScripts:'outside-only'});
  dom.window.document.querySelector('a').dataset.embed = src;
  dom.window.eval(fs.readFileSync('wordpress/prc-page-speed/video.js', 'utf8'));
  return dom;
}

test('no iframe before click; click creates original player with title and autoplay', () => {
  const dom = page();
  const doc = dom.window.document;
  assert.equal(doc.querySelector('iframe'), null);
  doc.querySelector('span').click();
  const frame = doc.querySelector('iframe');
  assert.equal(frame.title, 'TEST-TITLE');
  assert.equal(new URL(frame.src).searchParams.get('autoplay'), '1');
  assert.equal(new URL(frame.src).searchParams.get('feature'), 'oembed');
  assert.equal(frame.allowFullscreen, true);
  assert.equal(doc.querySelector('a'), null);
});

test('modified clicks keep the normal video link', () => {
  const dom = page();
  dom.window.document.querySelector('a').dispatchEvent(new dom.window.MouseEvent('click', {bubbles:true,ctrlKey:true}));
  assert.equal(dom.window.document.querySelector('iframe'), null);
});

test('unapproved iframe host is never loaded', () => {
  const dom = page('https://example.com/embed/IBwvcUYDFio');
  dom.window.document.querySelector('span').click();
  assert.equal(dom.window.document.querySelector('iframe'), null);
});
