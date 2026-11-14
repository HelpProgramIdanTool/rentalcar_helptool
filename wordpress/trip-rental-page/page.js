(function(){
if(!document.getElementById('rental')){
 const status=document.getElementById('tripStatusMessage');
 if(status){status.scrollIntoView({behavior:'instant',block:'start'});status.focus({preventScroll:true});}
 return;
}
const LOCATIONS={"cities": [["", "בחרו עיר"], ["OTHER", "עיר אחרת / מדינה אחרת"], ["Warszawa", "ורשה · Warszawa"], ["Kraków", "קרקוב · Kraków"], ["Katowice", "קטוביץ · Katowice"], ["Gdańsk", "גדנסק · Gdańsk"], ["Lublin", "לובלין · Lublin"], ["Łódź", "לודז׳ · Łódź"], ["Modlin", "מודלין · Modlin"], ["Olsztyn", "אולשטין · Olsztyn"], ["Poznań", "פוזנן · Poznań"], ["Rzeszów", "ז׳שוב · Rzeszów"], ["Szczecin", "שצ׳צ׳ין · Szczecin"], ["Wrocław", "ורוצלב · Wrocław"], ["Radom", "ראדום · Radom"], ["Bydgoszcz", "בידגושץ׳ · Bydgoszcz"], ["Pardubice", "פרדוביצה · Pardubice"], ["Budapest", "בודפשט · Budapest"], ["Vienna", "וינה · Vienna"], ["Bratislava", "ברטיסלבה · Bratislava"], ["Prague", "פראג · Prague"], ["Berlin", "ברלין · Berlin"], ["Vilnius", "וילנה · Vilnius"], ["Ostrava", "אוסטרבה · Ostrava"], ["Brno", "ברנו · Brno"], ["Lubin", "לובין · Lubin"]], "services": [["AIRPORT", "Аэропорт"], ["ADDRESS", "Доставка по адресу клиента"], ["CITY_BRANCH", "Отдел в городе"]], "foreign_cities": ["Pardubice", "Budapest", "Vienna", "Bratislava", "Prague", "Berlin", "Vilnius", "Ostrava", "Brno"]};
const labels=['רכב קטן','רכב סטנדרטי סדאן','רכב משפחתי / מנהלים גדול, סדאן','רכב סטיישן','רכב היברידי','קראסאובר SUV קטן','קראסאובר SUV בינוני','קראסאובר SUV גדול','רכב פרמיום סדאן','רכב פרמיום SUV קטן','רכב פרמיום SUV בינוני','רכב פרמיום SUV גדול','רכב של 7 מקומות','רכב 8/9 מקומות'];
labels.forEach(text=>{const label=document.createElement('label');label.className='choice choice-card';const input=document.createElement('input');input.type='checkbox';input.name='category';input.value=text;label.append(input,document.createTextNode(text));document.getElementById('categories').append(label)});
const form=document.getElementById('rental'),steps=[...document.querySelectorAll('.step')],next=document.getElementById('next'),back=document.getElementById('back');let step=0;
const pad=n=>String(n).padStart(2,'0'),clockPickers=[];
for(const picker of document.querySelectorAll('.time-picker')){
 const input=picker.querySelector('input'),open=picker.querySelector('.clock-open'),panel=picker.querySelector('.clock-panel'),display=picker.querySelector('.clock-value');
 const state={hour:10,minute:0};let initialized=false;
 const update=()=>{input.value=pad(state.hour)+':'+pad(state.minute*30);display.textContent=input.value;picker.querySelectorAll('.wheel').forEach(wheel=>{const part=wheel.dataset.part;wheel.querySelectorAll('.wheel-option').forEach((option,i)=>option.setAttribute('aria-selected',String(i===state[part])));wheel.setAttribute('aria-activedescendant',input.name+'-'+part+'-'+state[part]);});};
 const choose=(part,value,scroll=true)=>{const count=part==='hour'?24:2;state[part]=(value+count)%count;if(scroll)picker.querySelector(`.wheel[data-part="${part}"]`).scrollTop=state[part]*44;update();};
 picker.querySelectorAll('.wheel').forEach(wheel=>{const part=wheel.dataset.part,count=part==='hour'?24:2;let timer;
  for(let i=0;i<count;i++){const option=document.createElement('button');option.type='button';option.className='wheel-option';option.id=input.name+'-'+part+'-'+i;option.tabIndex=-1;option.setAttribute('role','option');option.textContent=pad(part==='minute'?i*30:i);option.addEventListener('click',()=>choose(part,i));wheel.append(option);}
  wheel.addEventListener('scroll',()=>{clearTimeout(timer);timer=setTimeout(()=>choose(part,Math.max(0,Math.min(count-1,Math.round(wheel.scrollTop/44))),false),90);});
  wheel.addEventListener('keydown',e=>{let value=state[part];if(e.key==='ArrowDown')value++;else if(e.key==='ArrowUp')value--;else if(e.key==='Home')value=0;else if(e.key==='End')value=count-1;else return;e.preventDefault();choose(part,value);});
 });
 picker.querySelectorAll('.wheel-up,.wheel-down').forEach(button=>button.addEventListener('click',()=>choose(button.dataset.part,state[button.dataset.part]+(button.classList.contains('wheel-up')?-1:1))));
 const flush=()=>{if(!panel.hidden)picker.querySelectorAll('.wheel').forEach(wheel=>{const count=wheel.dataset.part==='hour'?24:2;choose(wheel.dataset.part,Math.max(0,Math.min(count-1,Math.round(wheel.scrollTop/44))),false);});};
 const close=()=>{flush();panel.hidden=true;open.setAttribute('aria-expanded','false');};
 open.addEventListener('click',()=>{if(!panel.hidden){close();return;}clockPickers.forEach(p=>p.close());panel.hidden=false;open.setAttribute('aria-expanded','true');requestAnimationFrame(()=>{choose('hour',state.hour);choose('minute',state.minute);initialized=true;});});
 picker.querySelector('.clock-done').addEventListener('click',()=>{close();validateStep(false);open.focus();});
 clockPickers.push({close,flush});update();
}
for(const side of ['pickup','return']){
 const city=form.elements[side+'City'];LOCATIONS.cities.forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;city.append(option);});
 city.addEventListener('change',()=>{document.getElementById(side+'OtherBox').hidden=city.value!=='OTHER';syncForeign();validateStep(false);});
 const service=form.elements[side+'Place'];service.addEventListener('change',()=>{document.getElementById(side+'AddressBox').hidden=service.value!=='ADDRESS';validateStep(false);});
 form.elements[side+'Country'].addEventListener('input',syncForeign);
}

function displayDateToISO(value){const m=/^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value||'');return m?`${m[3]}-${m[2]}-${m[1]}`:'';}
for(const side of ['pickup','return']){
 const field=form.elements[side+'Date'],calendar=document.getElementById(side+'Calendar');
 field.addEventListener('input',()=>{const digits=field.value.replace(/\D/g,'').slice(0,8);field.value=digits.slice(0,2)+(digits.length>2?'.'+digits.slice(2,4):'')+(digits.length>4?'.'+digits.slice(4):'');});
 calendar.addEventListener('change',()=>{field.value=calendar.value.split('-').reverse().join('.');field.dispatchEvent(new Event('change'));});
 document.getElementById(side+'CalendarButton').addEventListener('click',()=>{calendar.value=displayDateToISO(field.value);if(calendar.showPicker)calendar.showPicker();else calendar.focus();});
}

function tripData(){clockPickers.forEach(p=>p.flush());const d=Object.fromEntries(new FormData(form));for(const side of ['pickup','return'])d[side+'Date']=displayDateToISO(d[side+'Date']);return d;}
function syncDates(){const today=TripValidation.wallParts(Date.now()).date,pickup=displayDateToISO(form.elements.pickupDate.value);document.getElementById('pickupCalendar').min=today;document.getElementById('returnCalendar').min=pickup>today?pickup:today;}
function syncForeign(){const foreign=['pickup','return'].some(side=>{const city=form.elements[side+'City'].value,country=form.elements[side+'Country'].value.trim().toLowerCase();return LOCATIONS.foreign_cities.includes(city)||(city==='OTHER'&&country&&!['poland','polska','pl','פולין'].includes(country));});const abroad=form.elements.abroad;abroad.options[0].disabled=foreign;if(foreign)abroad.value='כן';document.getElementById('foreign-note').hidden=!foreign;document.getElementById('countries').hidden=abroad.value==='לא';}
function validateStep(focus){
 if(step!==1)return true;syncDates();const d=tripData(),errors=[];const allowed=new Set(LOCATIONS.cities.map(([value])=>value));
 for(const side of ['pickup','return']){
  if(!d[side+'City']||!allowed.has(d[side+'City']))errors.push({field:side+'City',message:side==='pickup'?'בחרו עיר קבלה מהרשימה.':'בחרו עיר החזרה מהרשימה.'});
  if(!LOCATIONS.services.some(([code])=>code===d[side+'Place']))errors.push({field:side+'Place',message:'בחרו מקום מהרשימה.'});
  if(d[side+'City']==='OTHER'){
   if(!d[side+'Country'].trim())errors.push({field:side+'Country',message:'ציינו מדינה עבור המקום האחר.'});
   if(!d[side+'OtherCity'].trim())errors.push({field:side+'OtherCity',message:'ציינו עיר או מקום עבור האפשרות האחרת.'});
  }
  if(d[side+'Place']==='ADDRESS'&&!d[side+'Address'].trim())errors.push({field:side+'Address',message:'ציינו שם מלון וכתובת למסירה / החזרה.'});
 }
 const result=TripValidation.validateTrip(d);errors.push(...result.errors);
 form.querySelectorAll('.bad-field').forEach(el=>{el.classList.remove('bad-field');el.removeAttribute('aria-invalid');});
 const visibleErrors=focus?errors:errors.filter(e=>d[e.field]&&!(e.field.endsWith('Time')&&!d[e.field.replace('Time','Date')]));
 document.getElementById('dateError').textContent=visibleErrors.map(e=>e.message).join('\n');
 for(const error of visibleErrors){const field=form.elements[error.field],target=field?.type==='hidden'?field.closest('.time-picker').querySelector('.clock-open'):field;if(target){target.classList.add('bad-field');target.setAttribute('aria-invalid','true');}}
 if(focus&&errors.length){const field=form.elements[errors[0].field];(field?.type==='hidden'?field.closest('.time-picker').querySelector('.clock-open'):field)?.focus();}
 return !errors.length;
}
for(const name of ['pickupDate','returnDate','pickupTime','returnTime'])form.elements[name].addEventListener('change',()=>{syncDates();validateStep(false);});
function formatDate(date){return date?date.split('-').reverse().join('.'):'לא צוין';}
function placeLabel(d,side){const city=d[side+'City']==='OTHER'?[d[side+'OtherCity'],d[side+'Country']].filter(Boolean).join(', '):LOCATIONS.cities.find(([value])=>value===d[side+'City'])?.[1]||'לא צוין';return city+' · '+form.elements[side+'Place'].selectedOptions[0].textContent+(d[side+'Address']?' · '+d[side+'Address']:'');}
function show(){document.getElementById('formError').hidden=true;steps.forEach((s,i)=>s.hidden=i!==step);document.querySelectorAll('.progress i').forEach((s,i)=>s.classList.toggle('done',i<=step));document.getElementById('stepLabel').textContent=`שלב ${step+1} מתוך 5 · ${steps[step].dataset.title}`;next.textContent=step===4?'שליחת הבקשה ←':'ממשיכים ←';back.hidden=step===0;
 if(step===1)syncDates();if(step===3)syncForeign();
 if(step===4){const d=tripData(),all=new FormData(form),get=n=>d[n]||'לא צוין';document.getElementById('summary').textContent=`שם: ${get('name')}\nדוא״ל: ${get('email')}\nטלפון: ${get('phone')}\n\nקבלה: ${placeLabel(d,'pickup')}\n${formatDate(d.pickupDate)} · ${d.pickupTime}\nהחזרה: ${placeLabel(d,'return')}\n${formatDate(d.returnDate)} · ${d.returnTime}\n\nנוסעים: ${get('passengers')} · מזוודות: ${get('bags')} · ${get('gear')}\nקבוצות רכב: ${all.getAll('category').join(' / ')||'לא נבחרו'}\nיציאה מחוץ לפולין: ${get('abroad')}\nמדינות: ${get('countries')}\nתוספות: ${[['childSeats','כיסא / בוסטר'],['gps','GPS'],['chains','שרשראות שלג'],['advice','המלצה']].filter(([n])=>all.has(n)).map(([,t])=>t).join(', ')||'לא נבחרו'}\nהערות: ${get('notes')}`;}
}
next.addEventListener('click',()=>{if(step===4){const d=tripData();if(TripValidation.validateTrip(d).errors.length){step=1;show();validateStep(true);return;}tripSend();return;}if(step===1&&!validateStep(true))return;for(const field of steps[step].querySelectorAll('input,select,textarea')){if(!field.checkValidity()){validateFields(steps[step]);return;}}clockPickers.forEach(p=>p.close());step++;show();form.scrollIntoView({behavior:'instant',block:'start'});});
back.addEventListener('click',()=>{clockPickers.forEach(p=>p.close());step--;show();form.scrollIntoView({behavior:'instant',block:'start'});});form.addEventListener('submit',e=>e.preventDefault());form.elements.abroad.addEventListener('change',syncForeign);syncDates();show();

function tripSend(){
 const d=tripData();
 for(const section of steps){for(const field of section.querySelectorAll('input,select,textarea')){if(!field.checkValidity()){step=steps.indexOf(section);show();validateFields(section);return;}}}
 const payload={trip_ui:JSON.stringify({...d,category:new FormData(form).getAll('category')}),full_name:d.name,email:d.email,phone:d.phone,driver_age:d.age,pickup_city:d.pickupCity,pickup_place:form.elements.pickupPlace.selectedOptions[0].textContent,pickup_date:d.pickupDate,pickup_time:d.pickupTime,dropoff_city:d.returnCity,dropoff_place:form.elements.returnPlace.selectedOptions[0].textContent,dropoff_date:d.returnDate,dropoff_time:d.returnTime,location_notes:[placeLabel(d,'pickup'),placeLabel(d,'return')].join(' / '),passengers:d.passengers,luggage:d.bags,transmission:d.gear,abroad:d.abroad,abroad_countries:d.countries,child_seats:d.childSeats?'כן':'לא',child_seat_count:'',gps:d.gps?'כן':'לא',snow_chains:d.chains?'כן':'לא',notes:d.notes,confirm:'כן',action:'trip_car_request_submit',form_started:TRIP_CONFIG.started,trip_car_request_nonce:TRIP_CONFIG.nonce};
 if(d.pickupCity==='OTHER')payload.pickup_city=[d.pickupOtherCity,d.pickupCountry].join(', ');
 if(d.returnCity==='OTHER')payload.dropoff_city=[d.returnOtherCity,d.returnCountry].join(', ');
 const post=document.getElementById('tripPost');post.action=TRIP_CONFIG.action;post.replaceChildren();
 const add=(name,value)=>{const el=document.createElement('input');el.type='hidden';el.name=name;el.value=value;post.append(el);};
 Object.entries(payload).forEach(([k,v])=>add(k,v??''));new FormData(form).getAll('category').forEach(v=>add('car_group[]',v));
 if(d.advice)add('priorities[]','צריך המלצה על תוספות');
 next.disabled=true;next.textContent='שולחים…';post.submit();
}

if(TRIP_CONFIG.restore && Object.keys(TRIP_CONFIG.restore).length){
 const r=TRIP_CONFIG.restore,map={driver_age:'age',full_name:'name',phone:'phone',email:'email',pickup_city:'pickupCity',pickup_date:'pickupDate',pickup_time:'pickupTime',dropoff_city:'returnCity',dropoff_date:'returnDate',dropoff_time:'returnTime',passengers:'passengers',luggage:'bags',transmission:'gear',abroad:'abroad',abroad_countries:'countries',notes:'notes'};
 for(const [source,target] of Object.entries(map)){const el=form.elements[target];if(el&&r[source])el.value=target.endsWith('Date')?r[source].split('-').reverse().join('.'):r[source];}
 for(const el of form.querySelectorAll('[name="category"]'))el.checked=(r.car_group||[]).includes(el.value);
 for(const [source,target] of Object.entries({child_seats:'childSeats',gps:'gps',snow_chains:'chains'}))form.elements[target].checked=r[source]==='כן';
 syncDates();syncForeign();show();
}

if(TRIP_CONFIG.restore?.trip_ui){
 try {const saved=JSON.parse(TRIP_CONFIG.restore.trip_ui);
 for(const [name,value] of Object.entries(saved)){if(name==='category'){for(const el of form.querySelectorAll('[name="category"]'))el.checked=Array.isArray(value)&&value.includes(el.value);continue;}const el=form.elements[name];if(!el||typeof value!=='string')continue;if(el.type==='checkbox')el.checked=!!value;else el.value=name.endsWith('Date')?formatDate(value):value;}
 for(const side of ['pickup','return']){document.getElementById(side+'OtherBox').hidden=form.elements[side+'City'].value!=='OTHER';document.getElementById(side+'AddressBox').hidden=form.elements[side+'Place'].value!=='ADDRESS';}
 syncDates();syncForeign();show();}catch(e){console.warn('Saved form could not be restored');}
}

function validateFields(section){
 const errors=[];
 section.querySelectorAll('input,select,textarea').forEach(field=>{
  const message=TripValidation.fieldMessage(field);
  const id='trip-error-'+field.name;
  let note=document.getElementById(id);
  if(message){
   errors.push({field,message});field.classList.add('bad-field');field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby',id);
   if(!note){note=document.createElement('span');note.id=id;note.className='trip-field-error';field.closest('label').append(note);}note.textContent=message;
  }else{field.classList.remove('bad-field');field.removeAttribute('aria-invalid');if(note){note.remove();field.removeAttribute('aria-describedby');}}
 });
 const banner=document.getElementById('formError');banner.hidden=!errors.length;
 if(errors.length){banner.textContent='יש לתקן את הפרטים המסומנים: '+errors.map(e=>e.message).join(' ');errors[0].field.focus({preventScroll:true});errors[0].field.scrollIntoView({behavior:'instant',block:'center'});}
 return !errors.length;
}
form.addEventListener('input',e=>{if(e.target.getAttribute('aria-invalid')==='true')validateFields(steps[step]);});
if(document.getElementById('tripStatusMessage'))document.getElementById('tripStatusMessage').scrollIntoView({behavior:'instant',block:'start'});
})();
