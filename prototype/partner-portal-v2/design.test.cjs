const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('../../tmp/wordpress-qa/node_modules/jsdom');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const script=fs.readFileSync(path.join(__dirname,'design.js'),'utf8');
function page(hash='home') {
 const dom=new JSDOM(html,{url:'http://localhost/#'+hash,runScripts:'outside-only'});
 dom.window.eval(script);
 return dom;
}
function change(w,el){el.dispatchEvent(new w.Event('change',{bubbles:true}));}

test('all fourteen categories are available and duplicate choice synchronises',()=>{
 const dom=page('options'),w=dom.window,d=w.document;
 assert.equal(d.querySelectorAll('.category').length,14);
 const inputs=[...d.querySelectorAll('[data-pick="kaizen-f"]')];
 assert.equal(inputs.length,2);inputs[0].checked=true;change(w,inputs[0]);
 assert.equal(inputs[1].checked,true);assert.equal(inputs[1].disabled,true);
 assert.equal(inputs[1].closest('tr').querySelector('[data-already]').hidden,false);
 inputs[0].checked=false;change(w,inputs[0]);
 assert.equal(inputs[1].disabled,false);assert.equal(inputs[1].checked,false);
 dom.window.close();
});
test('customer email becomes required only for the explicit customer delivery choice',()=>{
 const dom=page('review'),w=dom.window,d=w.document;
 const email=d.querySelector('[name="clientEmail"]');assert.equal(email.required,false);
 const both=d.querySelector('[value="both"]');both.checked=true;change(w,both);
 assert.equal(email.required,true);assert.equal(d.querySelector('#client-email').hidden,false);
 assert.ok(d.body.textContent.includes('idan.caliber@gmail.com'));
 const partner=d.querySelector('[value="partner"]');partner.checked=true;change(w,partner);
 assert.equal(email.required,false);dom.window.close();
});
test('dates use dot format, half-hour controls have 48 choices and confirmations start checked',()=>{
 const dom=page('trip'),d=dom.window.document;
 assert.equal(d.querySelector('[name="time"]').options.length,48);
 assert.equal(d.querySelector('[name="returnTime"]').options[47].value,'23:30');
 assert.match(d.querySelector('[name="from"]').value,/^\d{2}\.\d{2}\.\d{4}$/);
 for(const n of ['driverOk','cardOk','borderOk'])assert.equal(d.querySelector('[name='+n+']').checked,true);
 d.querySelector('[name="from"]').value='31.02.2026';
 d.querySelector('#trip-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
 assert.equal(dom.window.location.hash,'#trip');assert.equal(d.querySelector('#toast').hidden,false);
 dom.window.close();
});
test('invoice and second-driver details are explicit and conditionally required',()=>{
 const dom=page('book'),d=dom.window.document,w=dom.window;
 const second=d.querySelector('#additional-driver');second.checked=true;change(w,second);
 assert.equal(d.querySelector('[name="secondDriver"]').required,true);
 const invoice=d.querySelector('#invoice-toggle');invoice.checked=true;change(w,invoice);
 assert.equal(d.querySelector('[name="invoiceName"]').required,true);
 assert.equal(d.querySelector('[name="invoiceAddress"]').required,true);
 dom.window.close();
});
test('change request is directed to Idan and keeps existing booking unchanged',()=>{
 const dom=page('detail'),d=dom.window.document;
 d.querySelector('[data-action="request-change"]').click();
 assert.match(d.querySelector('#dialog-content').textContent,/לעידן/);
 d.querySelector('#change-form textarea').value='TEST CHANGE';
 d.querySelector('#change-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
 assert.match(d.querySelector('main').textContent,/ההזמנה הקיימת לא שונתה/);
 assert.match(d.querySelector('main').textContent,/מאושרת/);
 dom.window.close();
});
test('nine-step guided presentation navigates login, partner workflow and owner access',()=>{
 const dom=page(),d=dom.window.document;
 d.querySelector('#present').click();
 assert.equal(d.querySelector('#tour').hidden,false);
 for(let i=0;i<8;i++)d.querySelector('#tour-next').click();
 assert.match(d.querySelector('#tour-count').textContent,/9 \/ 9/);
 assert.equal(dom.window.location.hash,'#owner');
 d.querySelector('#tour-next').click();assert.equal(d.querySelector('#tour').hidden,true);
 dom.window.close();
});

test('owner can switch cabinets and the selected cabinet does not mix another partner history',()=>{
 const dom=page('owner'),d=dom.window.document;
 d.querySelector('[data-open-partner="2"]').click();
 dom.window.dispatchEvent(new dom.window.HashChangeEvent('hashchange'));
 assert.match(d.querySelector('#partner-name').textContent,/נוסף/);
 assert.doesNotMatch(d.querySelector('main').textContent,/DEMO-R-0082/);
 assert.match(d.querySelector('.owner-banner').textContent,/עידן/);
 dom.window.close();
});
