const test = require('node:test');
const assert = require('node:assert/strict');
const {matchCategory} = require('../../quotes/static/quotes/booking_paste.js');

test('choose the category only inside the selected supplier', () => {
  const options = [{value:'1',textContent:'TEST FIRM — SUV MEDIUM AT (TEST-A)'},
                   {value:'2',textContent:'OTHER FIRM — SUV MEDIUM AUT (TEST-B)'}];
  assert.equal(matchCategory('SUV MEDIUM AUT', options, 'OWNER-CHOICE',
    {'1':'OWNER-CHOICE','2':'OTHER'}), '1');
  assert.equal(matchCategory('SUV MEDIUM AUT', options, '', {'1':'OWNER-CHOICE'}), '');
});
test('do not guess between two matching groups or missing categories', () => {
  const options = [{value:'1',textContent:'TEST CATEGORY (TEST-A)'},
                   {value:'2',textContent:'TEST CATEGORY (TEST-B)'}];
  assert.equal(matchCategory('TEST CATEGORY', options, 'X', {'1':'X','2':'X'}), '');
  assert.equal(matchCategory('DIFFERENT CATEGORY', options, 'X', {'1':'X','2':'X'}), '');
});
