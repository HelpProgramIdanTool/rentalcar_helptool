const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('../../tmp/wordpress-qa/node_modules/jsdom');
function page(){const dom=new JSDOM(fs.readFileSync(path.join(__dirname,'index.html'),'utf8'),{url:'http://localhost/',runScripts:'outside-only'});dom.window.eval(['cities.js','workspace.js','workspace-main.js'].map(f=>fs.readFileSync(path.join(__dirname,f),'utf8')).join('\n'));return dom;}
function change(w,el){el.dispatchEvent(new w.Event('change',{bubbles:true}));}
function submit(w,el){el.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));}
test('one continuous page contains trip, vehicles, offer and order with full configured cities',()=>{
 const dom=page(),d=dom.window.document;
 for(const id of ['trip','options','review','book'])assert.ok(d.getElementById(id));
 assert.equal(dom.window.PRC_DESIGN_CITIES.length,24);
 for(const name of ['pickupCity','returnCity']){
  const values=[...d.querySelector('[name='+name+']').options].map(o=>o.value);
  for(const city of ['Warszawa','Kraków','Gdańsk','Modlin','Łódź','Lubin','Prague','Pardubice','Berlin','Vienna','Bratislava','OTHER'])assert.ok(values.includes(city));
 }
 assert.equal(d.querySelectorAll('.category').length,14);
 assert.ok(d.querySelector('#options .company-compare').open);
 dom.window.close();
});
test('real native calendar writes dotted dates and return cannot predate pickup calendar',()=>{
 const dom=page(),w=dom.window,d=w.document;
 const pick=d.querySelector('[data-date=pickup]');pick.value='2027-01-23';change(w,pick);
 assert.equal(d.querySelector('[name=pickupDate]').value,'23.01.2027');
 assert.equal(d.querySelector('[name=returnDate]').value,'23.01.2027');
 assert.equal(d.querySelector('[data-date=return]').min,'2027-01-23');
 assert.equal(d.querySelector('[name=pickupTime]').options.length,48);
 d.querySelector('[name=pickupDate]').value='24.01.2027';d.querySelector('[name=pickupDate]').dispatchEvent(new w.Event('input',{bubbles:true}));
 assert.equal(pick.value,'2027-01-24');dom.window.close();
});
test('selecting an offer keeps trip and driver fields mounted on the same page',()=>{
 const dom=page(),w=dom.window,d=w.document;
 const trip=d.querySelector('#journey-form');const driver=d.querySelector('[name=driverName]');
 d.querySelector('[name=customerName]').value='TEST CUSTOMER';
 d.querySelector('[data-order-choice=mm-suv]').click();
 assert.equal(d.querySelector('#journey-form'),trip);
 assert.equal(d.querySelector('[name=customerName]').value,'TEST CUSTOMER');
 assert.equal(d.querySelector('[name=driverName]'),driver);
 assert.equal(d.querySelector('#order-fields').disabled,false);
 assert.match(d.querySelector('#selected-vehicle').textContent,/MM Cars/);
 assert.equal(w.location.hash,'');dom.window.close();
});
test('one selected group is mirrored across categories and cannot be added twice',()=>{
 const dom=page(),w=dom.window,d=w.document;
 const inputs=[...d.querySelectorAll('[data-choice=kaizen-f]')];
 inputs[0].checked=true;change(w,inputs[0]);
 assert.equal(inputs[1].disabled,true);assert.equal(inputs[1].checked,true);
 assert.equal(d.querySelectorAll('[data-order-choice=kaizen-f]').length,1);
 dom.window.close();
});
test('invoice, client email and order review expand inline; selected order is not sent twice',()=>{
 const dom=page(),w=dom.window,d=w.document;
 const both=d.querySelector('[name=recipient][value=both]');both.checked=true;change(w,both);
 assert.equal(d.querySelector('[name=customerEmail]').required,true);
 d.querySelector('[data-order-choice=mm-suv]').click();
 const values={driverName:'TEST DRIVER',driverPhone:'0000',driverEmail:'test@example.invalid'};
 for(const [name,value] of Object.entries(values))d.querySelector('[name='+name+']').value=value;
 const invoice=d.querySelector('[name=invoice]');invoice.checked=true;change(w,invoice);
 d.querySelector('[name=invoiceName]').value='TEST COMPANY';d.querySelector('[name=invoiceAddress]').value='TEST ADDRESS';
 d.querySelector('[name=checked]').checked=true;
 submit(w,d.querySelector('#order-form'));
 assert.equal(d.querySelector('#order-review').hidden,false);
 assert.match(d.querySelector('#order-review').textContent,/TEST COMPANY/);
 assert.match(d.querySelector('#order-review').textContent,/MM Cars/);
 d.querySelector('#send-order').click();assert.equal(d.querySelector('#send-order').disabled,true);
 assert.match(d.querySelector('#booking-result').textContent,/ממתינה לאישור/);
 assert.equal(d.querySelectorAll('#booking-result h3').length,1);dom.window.close();
});
test('typing an impossible date is rejected and changing order data invalidates its review',()=>{
 const dom=page(),w=dom.window,d=w.document;
 d.querySelector('[name=pickupDate]').value='31.02.2027';
 submit(w,d.querySelector('#journey-form'));
 assert.equal(d.querySelector('#trip-error').hidden,false);
 d.querySelector('#order-review').hidden=false;
 d.querySelector('[name=driverName]').dispatchEvent(new w.Event('input',{bubbles:true}));
 assert.equal(d.querySelector('#order-review').hidden,true);dom.window.close();
});
