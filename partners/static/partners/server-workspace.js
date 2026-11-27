'use strict';
(()=>{
const $=s=>document.querySelector(s),root=$('#workspace');if(!root)return;
const testMode=root.dataset.testMode==='true';
const state={options:[],selected:new Set(),records:[],record:null,option:null,dirty:true,busy:false};
const csrf=$('[name=csrfmiddlewaretoken]').value;
const tripDates=window.PartnerTripDates;
function warsawToday(){return new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Warsaw',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date()).replaceAll('/','.');}
function calendarMinimum(){return tripDates.minimum(warsawToday(),$('[name=pickup_date]').value,$('[name=pickup_time]').value,dateTarget?.name==='return_date');}
function reconcileTripDates(){
 const pickup=$('[name=pickup_date]'),returned=$('[name=return_date]'),startTime=$('[name=pickup_time]'),endTime=$('[name=return_time]');
 const sameDay=tripDates.parse(pickup.value)!==null&&tripDates.parse(pickup.value)===tripDates.parse(returned.value);
 for(const option of endTime.options)option.disabled=sameDay&&!!option.value&&option.value<=startTime.value;
 const invalid=tripDates.reversed(pickup.value,startTime.value,returned.value,endTime.value);
 const message=invalid?'מועד ההחזרה חייב להיות אחרי מועד הקבלה. נא לתקן את תאריך ההחזרה או את השעה.':'';
 const sameDayInvalid=invalid&&sameDay;
 returned.setCustomValidity(invalid&&!sameDay?message:'');
 endTime.setCustomValidity(sameDayInvalid?message:'');
 for(const input of [returned,endTime])input.removeAttribute('aria-invalid');
 if(invalid)(sameDayInvalid?endTime:returned).setAttribute('aria-invalid','true');
 $('#return-date-error').textContent=message;$('#return-date-error').hidden=!invalid;
 $('#calculate').disabled=state.busy||invalid;
}
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=(v,c)=>new Intl.NumberFormat('he-IL',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(v))+' '+c;
const status={SENT:'ההצעה נשלחה',SEND_FAILED:'השליחה לא אושרה — יש לפנות לעידן',CANCELLED:'בוטלה',COMPLETED:'הסתיימה',ACTIVE:'פעילה',DRAFT:'טיוטה',QUOTED:testMode?'הצעת בדיקה שמורה':'הצעה שמורה',WAITING:testMode?'הזמנת בדיקה — ממתינה לאישור':'ממתינה לאישור',CONFIRMED:'אושרה על ידי עידן',MANUAL:'ממתינה לבדיקה של עידן'};
function notify(text){$('#notification').textContent=text;$('#notification').hidden=false;}
function errors(data){if(data.error)return data.error;return Object.entries(data.errors||{}).map(([key,items])=>key+': '+items.map(x=>x.message).join(' ')).join('\n')||'לא ניתן להשלים את הפעולה.';}
async function api(payload){const response=await fetch(root.dataset.actionUrl,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(payload),credentials:'same-origin'});if(!response.ok){let data;try{data=await response.json();}catch{throw Error('לא ניתן להשלים את הפעולה. נסו לרענן ולהיכנס מחדש.');}const failure=Error(errors(data));failure.fields=data.errors;throw failure;}return response.json();}
function showErrors(error,form){
 const box=form.id==='trip-form'?$('#field-errors'):form.id==='order-form'?$('#order-errors'):$('#notification');
 document.querySelectorAll('[aria-invalid=true]').forEach(input=>input.removeAttribute('aria-invalid'));
 const messages=[];
 for(const [name,items] of Object.entries(error.fields||{})){
  const input=form.elements.namedItem(name);
  if(input?.setAttribute)input.setAttribute('aria-invalid','true');
  const label=input?.labels?.[0]?.textContent.trim()||'';
  messages.push(label+': '+items.map(item=>item.message).join(' '));
 }
 box.textContent=messages.length?messages.join('\n'):error.message;box.hidden=false;
 box.setAttribute('tabindex','-1');box.focus();box.scrollIntoView?.({block:'center'});
}
function validateTripDates(){
 const fields={};const dates={};
 for(const side of ['pickup','return']){
  const value=$('[name='+side+'_date]').value;
  const match=/^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value);
  const date=match?new Date(+match[3],+match[2]-1,+match[1]):null;
  if(!date||date.getFullYear()!==+match[3]||date.getMonth()!==+match[2]-1||date.getDate()!==+match[1])fields[side+'_date']=[{message:'נא להזין תאריך תקין בפורמט DD.MM.YYYY.'}];
  else dates[side]=match[3]+'-'+match[2]+'-'+match[1]+'T'+$('[name='+side+'_time]').value;
 }
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).map(p=>[p.type,p.value]));
 const now=parts.year+'-'+parts.month+'-'+parts.day+'T'+parts.hour+':'+parts.minute;
 if(dates.pickup&&dates.pickup<=now)fields.pickup_date=[{message:'מועד הקבלה כבר עבר. נא לבחור תאריך ושעה עתידיים.'}];
 if(dates.pickup&&dates.return&&dates.return<=dates.pickup)fields.return_date=[{message:'ההחזרה חייבת להיות אחרי הקבלה.'}];
 if(Object.keys(fields).length){const error=Error();error.fields=fields;throw error;}
}
function clearTripErrors(){ $('#field-errors').hidden=true;$('#trip-form').querySelectorAll('[aria-invalid]').forEach(input=>input.removeAttribute('aria-invalid')); }
function trip(){const data=Object.fromEntries(new FormData($('#trip-form')));delete data.csrfmiddlewaretoken;for(const name of ['driver_ok','credit_ok','border_ok','cross_border','chains'])data[name]=$('[name='+name+']').checked;return data;}
function fingerprint(){return JSON.stringify(trip());}
function stage(name){
 $('#trip-form').hidden=name!=='trip';
 $('#vehicle-section').hidden=name!=='vehicles';
 $('#workflow-progress').hidden=!name;
 document.querySelectorAll('[data-stage]').forEach(item=>{
  if(item.dataset.stage===name)item.setAttribute('aria-current','step');
  else item.removeAttribute('aria-current');
 });
 if(name==='preview'){$('#offer-detail').hidden=false;$('#order-editor').hidden=true;$('#offer-list').hidden=true;}
 if(name==='order'){$('#offer-detail').hidden=true;$('#order-editor').hidden=false;$('#offer-list').hidden=true;}
}
function tab(name){document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==name);document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-current',b.dataset.tab===name?'page':'false'));if(name==='new')stage('trip');else {stage(null);if(name==='offers'){$('#offer-list').hidden=false;$('#offer-detail').hidden=true;$('#order-editor').hidden=true;}if(name==='orders')$('#order-detail').hidden=true;refresh().catch(e=>notify(e.message));}}
async function refresh(){const response=await fetch(root.dataset.recordsUrl,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('יש להיכנס מחדש לקבינט.');state.records=(await response.json()).records;lists();}
function tripLine(t){return [t.pickup_city,t.pickup_date,t.pickup_time,'←',t.return_city,t.return_date,t.return_time].filter(Boolean).join(' · ');}
function lists(){for(const [kind,id] of [['QUOTE','offer-list'],['ORDER','order-list']]){const rows=state.records.filter(r=>r.kind===kind);$('#'+id).innerHTML=rows.length?'<article>'+rows.map(r=>`<div class="record-line"><div><strong><bdi>${esc(r.number)}</bdi> · ${esc(r.customer_name)}</strong><small>${esc(tripLine(r.trip))}</small><span class="status">${esc(status[r.status]||r.status)}</span></div><button type="button" data-open="${r.id}">${kind==='QUOTE'?'פתיחת ההצעה':(testMode?'צפייה בהזמנת הבדיקה':'צפייה בהזמנה')} ←</button></div>`).join('')+'</article>':'<article><p>עדיין אין כאן '+(kind==='QUOTE'?'הצעות':'הזמנות')+'.</p><button data-tab="new" type="button">לתת הצעה חדשה</button></article>';}}
function categories(){const names=[...new Set(state.options.flatMap(o=>o.categories))];$('#vehicle-options').innerHTML=names.map((name,index)=>`<details class="category"><summary>${esc(name)}</summary><div class="table-scroll"><table><thead><tr><th>בחירה</th><th>חברה וקבוצה</th><th>דגמים</th><th>מחיר לכל התקופה</th><th>פיקדון</th></tr></thead><tbody>${state.options.filter(o=>o.categories.includes(name)).map(o=>`<tr><td><input type="checkbox" data-pick="${o.id}" data-category="${index}" aria-label="בחירת ${esc(o.supplier+' '+o.name)}"><span class="elsewhere" hidden>כבר נבחר</span></td><td><strong>${esc(o.supplier)}</strong>${esc(o.name)}</td><td>${esc(o.models)}</td><td><strong>${esc(money(o.total,o.currency))}</strong></td><td>${esc(money(o.deposit,o.deposit_currency))}</td></tr>`).join('')}</tbody></table></div></details>`).join('');syncSelection();}
const selectionSources=new Map();
function syncSelection(){document.querySelectorAll('[data-pick]').forEach(input=>{const selected=state.selected.has(input.dataset.pick);input.checked=selected;const elsewhere=selected&&selectionSources.get(input.dataset.pick)!==input.dataset.category;input.disabled=elsewhere;input.closest('tr').classList.toggle('row-picked',selected);input.parentElement.querySelector('.elsewhere').hidden=!elsewhere;});$('#selected-count').textContent=state.selected.size+' אפשרויות נבחרו';$('#save-offer').disabled=state.dirty||!state.selected.size||state.busy;}
function openQuote(r){offerDeliveryState(r);$('#copy-result').hidden=true;$('#copy-fallback').hidden=true;state.record=r;state.option=null;$('#offer-preview').srcdoc=r.details.preview_html||'';$('#offer-preview').hidden=!r.details.preview_html;stage('preview');$('#offer-detail').hidden=false;$('#order-editor').hidden=true;$('#offer-heading').textContent=r.number+' · '+r.customer_name;$('#offer-trip').textContent=tripLine(r.trip);$('#saved-options').innerHTML=r.options.map((o,i)=>`<div class="saved-option"><h3><span class="number">${i+1}</span>${esc(o.supplier)} · ${esc(o.name)}</h3><p>${esc(o.models)}</p><p><strong>${esc(money(o.total,o.currency))}</strong> · פיקדון ${esc(money(o.deposit,o.deposit_currency))}</p><button class="primary" type="button" data-book="${o.id}">בחירת אפשרות זו והשלמת פרטי הנהגים ↓</button></div>`).join('');$('#send-form [name=send_customer]').checked=!!r.details.send_customer;$('#send-form [name=customer_email]').value=r.details.customer_email||'';$('#offer-detail').scrollIntoView?.({block:'start'});}
function offerDeliveryState(record){
 $('#offer-delivery-state').textContent=record.details.mail_sent?'ההצעה נשלחה בהצלחה, עם עותק לעידן.':testMode?'חשבון הבדיקה של עידן: מייל אמיתי לא נשלח.':'ההצעה מוכנה. מייל יישלח רק בלחיצה על כפתור השליחה.';
}
function editTrip(){
 if(!state.record)return;
 const form=$('#trip-form');
 for(const [name,value] of Object.entries(state.record.trip)){
  const input=form.elements.namedItem(name);if(!input)continue;
  if(input.type==='checkbox')input.checked=!!value;
  else if(name==='driver_requirements')input.value=JSON.stringify(value);
  else input.value=name.endsWith('_date')&&/^\d{4}-\d{2}-\d{2}$/.test(value)?value.split('-').reverse().join('.'):value;
 }
 document.dispatchEvent(new Event('driverdetailsloaded'));
 state.options=state.record.options;state.selected=new Set(state.options.map(o=>o.id));
 selectionSources.clear();const names=[...new Set(state.options.flatMap(o=>o.categories))];state.options.forEach(o=>selectionSources.set(o.id,String(names.indexOf(o.categories[0]))));
 state.dirty=true;categories();clearTripErrors();tab('new');
 $('#calculation-note').textContent='הנתונים הוחזרו לעריכה. לאחר התיקון חשבו מחדש וצרו הצעה מעודכנת. ההצעה השמורה נשארת ללא שינוי.';
 reconcileTripDates();$('#trip-form').scrollIntoView?.({block:'start'});
}
async function copyOffer(){
 const record=state.record;if(!record)return;
 const date=value=>/^\d{4}-\d{2}-\d{2}$/.test(value||'')?value.split('-').reverse().join('.'):value||'';
 const t=record.trip;
 const place=value=>({AIRPORT:"נמל תעופה",CITY_BRANCH:"סניף בעיר",ADDRESS:"מלון / כתובת"}[value]||value);
 const lines=['הצעת בדיקה · '+record.number,record.customer_name,
 'קבלה: '+[date(t.pickup_date),t.pickup_time,t.pickup_city,place(t.pickup_service),t.pickup_address].filter(Boolean).join(' · '),
 'החזרה: '+[date(t.return_date),t.return_time,t.return_city,place(t.return_service),t.return_address].filter(Boolean).join(' · '),
 ...record.options.map((o,i)=>`${i+1}. ${o.supplier} · ${o.name}\n${o.models}\nמחיר לכל התקופה: ${money(o.total,o.currency)} · פיקדון: ${money(o.deposit,o.deposit_currency)}`),
 'הצעת בדיקה בלבד. המחיר אינו אישור זמינות או הזמנה.'];
 const html=record.details.preview_html;
 const documentCopy=html?new DOMParser().parseFromString(html,'text/html'):null;
 documentCopy?.querySelectorAll('style,script').forEach(node=>node.remove());
 const text=documentCopy?documentCopy.body.textContent:lines.filter(Boolean).join('\n\n');
 const box=$('#copy-result');box.hidden=false;
 try{if(html&&window.ClipboardItem&&navigator.clipboard.write){await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([html],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})]);}else{await navigator.clipboard.writeText(text);}$('#copy-fallback').hidden=true;box.textContent='ההצעה הועתקה. אפשר להדביק במייל או בוואטסאפ.';}
 catch{const fallback=$('#copy-fallback');fallback.value=text;fallback.hidden=false;fallback.focus();fallback.select();box.textContent='הדפדפן חסם העתקה אוטומטית. הטקסט מסומן — העתיקו אותו ידנית.';}
}
function openOrder(r){$('#order-detail').hidden=false;$('#order-detail').innerHTML=`<h2>${esc(r.number)}</h2><span class="status">${esc(status[r.status]||r.status)}</span><p>${esc(tripLine(r.trip))}</p>${r.options.map(o=>`<p><strong>${esc(o.supplier)} · ${esc(o.name)} · ${esc(money(o.total,o.currency))}</strong></p>`).join('')}<p>נהג: ${esc(r.details.driver_name)} · נהג נוסף: ${esc(r.details.additional_driver||'ללא')}</p><p><bdi>${esc(r.details.phone)}</bdi> · <bdi>${esc(r.details.email)}</bdi></p>${(r.details.child_seat_details||[]).map((seat,i)=>'<p>'+esc(''+(i+1))+'. '+seatFields.map(([key,label])=>seat[key]?esc(label)+': '+esc(seat[key]):'').filter(Boolean).join(' / ')+'</p>').join('')}${r.details.invoice?`<p>חשבונית: ${esc(r.details.invoice_name)} · ${esc(r.details.invoice_address)}</p>`:''}<p>${r.is_test?'זו הזמנת בדיקה בלבד. לא נשלח מייל לחברת השכרה.':(r.details.mail_sent?'הבקשה נשלחה לחברת ההשכרה. שינוי וביטול — דרך עידן בלבד.':'ההזמנה שמורה אך השליחה לא אושרה. יש לפנות לעידן ואין לשלוח הזמנה נוספת.')}</p><form class="request-form" data-request="${r.id}"><h3>בקשת שינוי או ביטול לעידן</h3><label>סוג הבקשה<select name="type"><option value="change">שינוי</option><option value="cancel">ביטול</option></select></label><label>מה צריך לשנות?<textarea name="message" maxlength="3000" required></textarea></label><button class="primary">שמירת הבקשה לעידן</button><p>ההזמנה המקורית לא משתנה אוטומטית.</p></form>`;$('#order-detail').scrollIntoView?.({block:'start'});}
document.addEventListener('click',async event=>{const button=event.target.closest('button');if(!button)return;try{if(button.hasAttribute('data-back-trip')){tab('new');$('#trip-form').scrollIntoView?.({block:'start'});}if(button.hasAttribute('data-edit-trip'))editTrip();if(button.hasAttribute('data-back-offer')){stage('preview');$('#offer-detail').scrollIntoView?.({block:'start'});}if(button.hasAttribute('data-back-order')){$('#order-check').hidden=true;$('#order-form').scrollIntoView?.({block:'start'});}if(button.id==='copy-offer')await copyOffer();if(button.dataset.tab)tab(button.dataset.tab);if(button.dataset.open){const r=state.records.find(r=>r.id===button.dataset.open);if(r?.kind==='QUOTE')openQuote(r);if(r?.kind==='ORDER')openOrder(r);}if(button.dataset.book){if(state.orderRecordId!==state.record.id){$('#order-form').reset();renderSeats();renderDrivers();$('#order-errors').hidden=true;$('#order-form [name=phone]').value=state.record.trip.customer_phone||'';$('#order-form [name=email]').value=state.record.trip.customer_email||'';state.orderRecordId=state.record.id;}state.option=state.record.options.find(o=>o.id===button.dataset.book);stage('order');$('#order-check').hidden=true;$('#order-summary').textContent=state.option.supplier+' · '+state.option.name+' · '+money(state.option.total,state.option.currency)+' · פיקדון '+money(state.option.deposit,state.option.deposit_currency);$('#order-editor').scrollIntoView?.({block:'start'});}if(button.id==='save-offer'){if(state.dirty||!state.selected.size)return;button.disabled=true;const result=await api({action:'save',trip:trip(),selected:[...state.selected]});tab('offers');await refresh();openQuote(result.record);notify('ההצעה נשמרה בבסיס הנתונים.');button.disabled=false;}if(button.id==='confirm-test-order'){validateSeats();button.disabled=true;const result=await api({action:'order',id:state.record.id,option:state.option.id,details:orderData()});tab('orders');await refresh();openOrder(result.record);notify(result.message||'הזמנת הבדיקה כבר נשמרה.');}}catch(e){notify(e.message);if(button.id==='confirm-test-order')showErrors(e,$('#order-form'));if(button.id==='save-offer'||button.id==='confirm-test-order')button.disabled=false;}});
const seatFields=[['age','גיל בשנים','0','18'],['height','גובה בס״מ','1','250'],['weight','משקל בק״ג','1','150'],['type_number','סוג הכיסא / בוסטר']];
function renderDrivers(){
 const count=Number(state.record.trip.drivers||1);
 $('#order-form [name=additional_driver]').required=count>=2;
 $('#additional-driver-fields').innerHTML=Array.from({length:Math.max(0,count-2)},(_,i)=>`<label>שם נהג ${i+3} באנגלית<input name="driver_${i+3}_name" maxlength="200" required></label>`).join('');
 $('#additional-driver-fields').insertAdjacentHTML('beforeend',Array.from({length:count},(_,i)=>`<div class="fields"><label>נהג ${i+1} — גיל ביום הקבלה<input name="driver_${i+1}_age" type="number" min="18" max="100" step="1" required></label><label>נהג ${i+1} — ותק רישיון בחודשים ביום הקבלה<input name="driver_${i+1}_license_months" type="number" min="0" max="1019" step="1" required></label></div>`).join(''));
}
function renderSeats(){
 const count=Number(state.record.trip.seats||0);
 $('#child-seat-fields').innerHTML=Array.from({length:count},(_,i)=>`<fieldset><legend>כיסא ילדים ${i+1}</legend><p>חובה למלא לפחות אחד מהפרטים עבור כיסא זה.</p><div class="fields">${seatFields.map(([key,label,min,max])=>`<label>${label}<input name="child_seat_${i+1}_${key}" ${key==='type_number'?'type="text" maxlength="100"':`type="number" min="${min}" max="${max}" step="0.01"`}></label>`).join('')}</div></fieldset>`).join('');
}
function validateSeats(){
 const fields={};
 for(let i=1;i<=Number(state.record.trip.seats||0);i++){
  const inputs=seatFields.map(([key])=>$('#order-form [name=child_seat_'+i+'_'+key+']'));
  if(!inputs.some(input=>input.value.trim()))fields['child_seat_'+i+'_age']=[{message:'כיסא '+i+': חובה למלא לפחות גיל, גובה, משקל או סוג כיסא.'}];
 }
 if(Object.keys(fields).length){const error=Error();error.fields=fields;throw error;}
}
function seatSummary(data){
 return Array.from({length:Number(state.record.trip.seats||0)},(_,i)=>'<p>כיסא '+(i+1)+': '+seatFields.map(([key,label])=>data['child_seat_'+(i+1)+'_'+key]?esc(label)+': '+esc(data['child_seat_'+(i+1)+'_'+key]):'').filter(Boolean).join(' · ')+'</p>').join('');
}
function orderData(){const data=Object.fromEntries(new FormData($('#order-form')));data.invoice=$('#order-form [name=invoice]').checked;return data;}
document.addEventListener('submit',async event=>{const form=event.target;if(!['trip-form','send-form','order-form','manual-form'].includes(form.id)&&!form.dataset.request)return;event.preventDefault();try{if(form.id==='trip-form'){clearTripErrors();validateTripDates();const previousSelection=new Set(state.selected);state.options=[];categories();state.busy=true;state.dirty=true;state.selected.clear();syncSelection();$('#calculate').disabled=true;$('#calculate').textContent='מחשב…';const before=fingerprint();const result=await api({action:'calculate',trip:trip()});if(before!==fingerprint())throw Error('פרטי הנסיעה השתנו בזמן החישוב. חשבו שוב.');state.options=result.options;state.selected=new Set(state.options.filter(o=>previousSelection.has(o.id)).map(o=>o.id));const names=[...new Set(state.options.flatMap(o=>o.categories))];selectionSources.clear();state.options.forEach(o=>selectionSources.set(o.id,String(names.indexOf(o.categories[0]))));state.dirty=false;categories();$('#calculation-note').textContent=result.options.length?result.options.length+' אפשרויות חושבו לפי מחירוני השרת. מחיר אינו אישור זמינות.':'לא נמצא מחיר מלא. שמרו פנייה לעידן לבדיקה אישית.';if(result.message)$('#calculation-note').textContent=result.message;stage('vehicles');$('#vehicle-section').scrollIntoView?.({block:'start'});}else if(form.id==='send-form'){const d=Object.fromEntries(new FormData(form));const result=await api({action:testMode?'simulate_send':'send_offer',id:state.record.id,send_customer:form.elements.namedItem('send_customer').checked,customer_email:d.customer_email});if(result.record){state.record=result.record;offerDeliveryState(result.record);}notify(result.message);refresh();}else if(form.id==='order-form'){if(!state.record||!state.option)return;$('#order-errors').hidden=true;validateSeats();const d=orderData();$('#order-check').innerHTML=`<button type="button" data-back-order>→ חזרה לעריכת פרטי ההזמנה</button><h3>בדיקה לפני שמירה</h3><p><strong>${esc(state.option.supplier)} · ${esc(state.option.name)} · ${esc(money(state.option.total,state.option.currency))}</strong></p><p>${esc(tripLine(state.record.trip))}</p><p>נהג: ${esc(d.driver_name)} · נהג נוסף: ${esc(d.additional_driver||'ללא')}</p><p>${esc(d.phone)} · ${esc(d.email)}</p>${seatSummary(d)}${d.invoice?`<p>חשבונית: ${esc(d.invoice_name)} · ${esc(d.invoice_address)}</p>`:''}<p>${testMode?'חשבון בדיקה: נשמרת רשומת בדיקה בלבד. מייל לא נשלח לחברה או ללקוח.':'אישור ההזמנה ישלח בקשה אמיתית לחברת ההשכרה, עם עותק אליכם ולעידן. הבקשה כפופה לאישור.'}</p><button class="primary" id="confirm-test-order" type="button">${testMode?'שמירת הזמנת הבדיקה':'אישור ושליחת ההזמנה לחברה'}</button>`;$('#order-check').hidden=false;$('#order-check').scrollIntoView?.({block:'start'});}else if(form.id==='manual-form'){const result=await api({action:'manual',trip:trip(),message:form.elements.namedItem('message').value});notify(result.message||(testMode?'הפנייה נשמרה ללא שליחת מייל.':'הפנייה נשלחה לעידן.'));}else if(form.dataset.request){const result=await api({action:form.elements.namedItem('type').value,id:form.dataset.request,message:form.elements.namedItem('message').value});notify(result.message);}}catch(e){showErrors(e,form);}finally{state.busy=false;$('#calculate').disabled=false;$('#calculate').textContent='חישוב מחירים ↓';syncSelection();reconcileTripDates();}});
document.addEventListener('change',event=>{const input=event.target;if(input.dataset.pick){if(input.checked){state.selected.add(input.dataset.pick);selectionSources.set(input.dataset.pick,input.dataset.category);}else{state.selected.delete(input.dataset.pick);selectionSources.delete(input.dataset.pick);}syncSelection();}});
document.addEventListener('input',event=>{if(event.target.closest('#trip-form')){reconcileTripDates();state.dirty=true;$('#calculation-note').textContent='הפרטים השתנו — יש לחשב מחדש לפני שמירת הצעה.';syncSelection();}if(event.target.closest('#order-form'))$('#order-check').hidden=true;});
// Explicit month/day picker, preserving the project's DD.MM.YYYY convention.
let dateTarget=null,month=0,year=2026;const months=['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר'];
function calendar(){const selected=dateTarget.value;const offset=new Date(year,month,1).getDay(),count=new Date(year,month+1,0).getDate();$('#calendar-content').innerHTML=`<div class="calendar-nav"><button type="button" data-move="-1" aria-label="חודש קודם">‹</button><strong>${months[month]} ${year}</strong><button type="button" data-move="1" aria-label="חודש הבא">›</button></div><div class="calendar-grid">${['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','ש׳'].map(t=>'<span>'+t+'</span>').join('')}${'<span></span>'.repeat(offset)}${Array.from({length:count},(_,i)=>{const value=String(i+1).padStart(2,'0')+'.'+String(month+1).padStart(2,'0')+'.'+year;return `<button type="button" data-day="${value}" ${Date.UTC(year,month,i+1)<calendarMinimum()?'disabled aria-disabled="true"':''} class="${value===selected?'current':''}">${i+1}</button>`;}).join('')}</div>`;}
document.addEventListener('click',event=>{const b=event.target.closest('button');if(!b)return;if(b.dataset.dateTarget){dateTarget=document.getElementById(b.dataset.dateTarget);const values=dateTarget.value.split('.');let d=values.length===3?new Date(+values[2],+values[1]-1,+values[0]):new Date();const minimum=calendarMinimum();if(!Number.isFinite(d.getTime())||Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())<minimum){const first=new Date(minimum);d=new Date(first.getUTCFullYear(),first.getUTCMonth(),first.getUTCDate());}month=d.getMonth();year=d.getFullYear();calendar();$('#calendar').showModal();}if(b.dataset.move){const d=new Date(year,month+Number(b.dataset.move),1);year=d.getFullYear();month=d.getMonth();calendar();}if(b.dataset.day&&!b.disabled){dateTarget.value=b.dataset.day;dateTarget.dispatchEvent(new Event('input',{bubbles:true}));reconcileTripDates();$('#calendar').close();dateTarget.focus();}if(b.id==='calendar-close')$('#calendar').close();});
document.addEventListener('invalid',event=>{
 const input=event.target,form=input.closest('form');if(!form)return;
 if(form.id==='trip-form'){
  event.preventDefault();input.setAttribute('aria-invalid','true');
  const error=Error((input.labels?.[0]?.textContent.trim()||'')+': נא למלא ערך תקין. תאריך בפורמט DD.MM.YYYY.');
  showErrors(error,form);input.setAttribute('aria-invalid','true');
 }
},true);
document.addEventListener('change',event=>{if(['pickup_date','return_date','pickup_time','return_time'].includes(event.target.name))reconcileTripDates();});
reconcileTripDates();
refresh().catch(e=>notify(e.message));
})();
