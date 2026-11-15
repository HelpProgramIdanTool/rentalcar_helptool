const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'templates/quotes/new_inquiry.html'), 'utf8');
const sidebar = fs.readFileSync(path.join(__dirname, 'templates/quotes/sidebar.html'), 'utf8');
const declaration = source.match(/const form = [^\n]+;/)[0];
const start = source.indexOf("document.querySelector('#import-inquiry').addEventListener");
const handler = source.slice(start, source.indexOf('  const draftKey', start));

async function run(ok) {
  const field = (type = 'text', value = '') => ({type, value});
  const languageForm = {elements: {language: field('select-one', 'ru'), csrfmiddlewaretoken: field('hidden', 'LANGUAGE-CSRF')}};
  const fields = Object.fromEntries(['full_name','email','phone_1','preferred_language','pickup_date','return_date','customer_notes']
    .map(name => [name, field()]));
  fields.full_name.value = 'BEFORE IMPORT';
  fields.customer_notes.value = 'TEST WEBSITE EMAIL';
  fields.csrfmiddlewaretoken = field('hidden', 'INQUIRY-CSRF');
  for (const name of ['pickup_time', 'return_time']) {
    fields[name] = {...field('select-one'), options: [{value: '10:00'}], add(option) {this.options.push(option);}};
  }
  fields.cross_border_requested = {...field('checkbox'), checked:false};
  const groupChoices = ['TEST-GROUP-A','TEST-GROUP-B','TEST-OTHER'].map(value => ({...field('checkbox', value), checked:false}));
  const extras = ['NAVIGATION','SNOW_CHAINS'].map(value => ({...field('checkbox', value), checked:false}));
  const inquiryForm = {elements: fields, querySelectorAll(selector) {
    const name = selector.match(/\[name="([^"]+)"\]/)[1];
    return name === 'vehicle_groups' ? groupChoices : name === 'extra_choices' ? extras : fields[name] ? [fields[name]] : [];
  }};
  const button = {disabled:false, addEventListener(event, callback) {this.callback = callback;}};
  const result = {textContent:''};
  const imported = {value:''};
  let posted;
  const selected = [];
  const nodes = {'#import-inquiry':button,'#import-result':result,'#imported-inquiry':imported,'#id_customer_notes':fields.customer_notes};
  const document = {
    querySelector(selector) {return selector === 'form' ? languageForm : selector === '#inquiry-form' ? inquiryForm : nodes[selector];},
    getElementById(id) {
      return source.includes(`id="${id}"`) && id === 'inquiry-form' ? inquiryForm : undefined;
    },
  };
  assert.match(sidebar, /<form[^>]+operator_language/);
  const context = vm.createContext({document,
    FormData: class extends Map {}, Option: class {constructor(text,value) {this.text=text;this.value=value;}},
    fetch: async (_url, request) => {
      posted = request.body;
      return {ok, json:async()=>ok ? {fields:{full_name:'TEST IMPORTED NAME',email:'test@example.invalid',phone_1:'TEST-PHONE',
        preferred_language:'Hebrew',pickup_date:'01-12-2030',return_date:'03-12-2030',pickup_time:'14:15',return_time:'22:00',
        cross_border_requested:true,vehicle_groups:['TEST-GROUP-A','TEST-GROUP-B'],suppliers:['TEST-SUPPLIER'],extra_choices:['NAVIGATION']},
        warnings:['TEST WARNING']} : {error:'TEST IMPORT ERROR'}};
    },
    pickupText:fields.pickup_date,returnText:fields.return_date,pickupCalendar:{},returnCalendar:{},
    pickupService:{value:'AIRPORT'},returnService:{value:'AIRPORT'},
    isoDate:value=>value.split('-').reverse().join('-'),filterGroups:values=>selected.push(values),
    toggleAddresses(){},toggleChildSeats(){},updatePhones(){},syncCrossBorder(){},saveDraft(){},scheduleLookup(){},
  });
  vm.runInContext(declaration + '\n' + handler, context);
  await button.callback.call(button);
  assert.equal(button.disabled,false);
  assert.equal(posted.get('csrfmiddlewaretoken'),'INQUIRY-CSRF');
  assert.equal(languageForm.elements.language.value,'ru');
  if (ok) {
    assert.equal(fields.full_name.value,'TEST IMPORTED NAME');
    assert.equal(fields.email.value,'test@example.invalid');
    assert.equal(fields.phone_1.value,'TEST-PHONE');
    assert.equal(fields.pickup_time.value,'14:15');
    assert.equal(fields.return_time.value,'22:00');
    assert(fields.pickup_time.options.some(option=>option.value==='14:15'));
    assert.equal(fields.cross_border_requested.checked,true);
    assert.deepEqual(groupChoices.map(input=>input.checked),[true,true,false]);
    assert.deepEqual(extras.map(input=>input.checked),[true,false]);
    assert.equal(context.pickupCalendar.value,'2030-12-01');
    assert.equal(context.returnCalendar.value,'2030-12-03');
    assert.equal(imported.value,'1');
    assert.equal(selected.length,1);
    assert.match(result.textContent,/Готово/);
    assert.match(result.textContent,/TEST WARNING/);
  } else {
    assert.equal(fields.full_name.value,'BEFORE IMPORT');
    assert.equal(imported.value,'');
    assert.equal(result.textContent,'TEST IMPORT ERROR');
  }
}

(async()=>{
  await run(true);
  await run(false);
  process.stdout.write('Inquiry import: correct form with language selector first, fields, times, groups, extras and failed-response preservation passed.\n');
})().catch(error=>{console.error(error);process.exitCode=1;});
