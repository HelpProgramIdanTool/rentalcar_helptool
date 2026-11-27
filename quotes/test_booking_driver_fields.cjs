const {JSDOM}=require('../tmp/wordpress-qa/node_modules/jsdom');
const fs=require('fs'),assert=require('node:assert/strict');
const dom=new JSDOM('<form id="order-form"><input name="additional_driver"><div id="additional-driver-fields"></div></form>',{runScripts:'outside-only'});
const doc=dom.window.document;
dom.window.eval(fs.readFileSync('quotes/static/quotes/booking_driver_fields.js','utf8'));
const source=fs.readFileSync('partners/static/partners/server-workspace.js','utf8');
const render=source.slice(source.indexOf('function renderDrivers()'),source.indexOf('function renderSeats()'));
const run=new Function('state','$','document','Event',render+';renderDrivers();');
run({record:{trip:{drivers:2,driver_requirements:{exception:false,drivers:[]}}}},s=>doc.querySelector(s),doc,dom.window.Event);
const boxes=doc.querySelectorAll('[data-booking-driver]');assert.equal(boxes.length,2);
for(const box of boxes){assert.equal(box.querySelector('[data-driver-extra]').hidden,true);assert.equal(box.querySelector('input[type=number]').required,false);assert.equal(box.querySelector('input[type=number]').disabled,true);}
const toggle=boxes[0].querySelector('input[type=checkbox]');toggle.checked=true;toggle.dispatchEvent(new dom.window.Event('change',{bubbles:true}));
assert.equal(boxes[0].querySelector('[data-driver-extra]').hidden,false);
assert.equal(boxes[0].querySelector('input[type=number]').required,true);
assert.equal(boxes[1].querySelector('input[type=number]').required,false);
assert.equal(new dom.window.FormData(doc.querySelector('form')).has('driver_2_age'),false);
dom.window.close();console.log('Booking driver fields: standard hidden/optional, marked only required, unchecked omitted from POST.');
