(function(){
 document.querySelectorAll('[data-portal-date]').forEach(field=>field.addEventListener('input',()=>{
  const digits=field.value.replace(/\D/g,'').slice(0,8);
  field.value=digits.slice(0,2)+(digits.length>2?'.'+digits.slice(2,4):'')+(digits.length>4?'.'+digits.slice(4):'');
 }));
 const form=document.getElementById('option-form');
 if(form){
  const boxes=[...form.querySelectorAll('input[name="groups"]')];
  const selection=new PartnerSelection(boxes.map(b=>b.value),boxes.filter(b=>b.checked).map(b=>b.value));
  boxes.forEach((box,index)=>{
   const note=document.createElement('span');note.className='already-selected';note.hidden=true;
   const text=document.createElement('span');text.textContent='כבר נבחר';note.append(text);
   const jump=document.createElement('button');jump.type='button';jump.textContent='לשינוי';jump.className='selection-source';
   jump.addEventListener('click',()=>{const source=boxes[selection.state(index).source];if(!source)return;source.closest('.category').open=true;source.scrollIntoView({behavior:'instant',block:'center'});source.focus({preventScroll:true});});note.append(jump);box.after(note);
   box.addEventListener('change',()=>{selection.set(index,box.checked);sync();});
  });
  function sync(){
   boxes.forEach((box,index)=>{const state=selection.state(index);box.checked=state.checked;box.disabled=state.already;box.hidden=state.already;const note=box.nextElementSibling;note.hidden=!state.already;box.closest('tr').classList.toggle('selected-elsewhere',state.already);});
   document.getElementById('selection-count').textContent=selection.selectedIds().length;
   form.querySelectorAll('.category').forEach(section=>{const label=section.querySelector('.category-selected');const selected=section.querySelectorAll('input[name="groups"]:checked').length;if(label)label.textContent=selected?'נבחרו '+selected:'';});
  }
  sync();
  form.querySelectorAll('.pick-row').forEach(row=>row.addEventListener('click',event=>{if(event.target.closest('input,button,a'))return;const box=row.querySelector('input[name="groups"]');if(box.disabled)return;box.checked=!box.checked;box.dispatchEvent(new Event('change',{bubbles:true}));}));
  form.addEventListener('submit',e=>{if(!boxes.some(b=>b.checked)){e.preventDefault();alert('נא לבחור לפחות אפשרות אחת להצעה.');}});
 }
 document.querySelectorAll('.send-form').forEach(form=>form.addEventListener('submit',()=>{const button=form.querySelector('button');button.disabled=true;button.textContent='שולחים…';}));
})();
