/* Public forms collect facts only; the rental server applies supplier rules. */
(function () {
  function ready() {
    const old = document.querySelector('[name="driver_age"], select[name="age"]');
    if (!old || old.form.querySelector('[name="driver_requirements"]')) return;
    const en = !!old.closest('[lang="en"]'), form = old.form;
    const text = en ? {
      title:'A driver is under 24 or has held a licence for less than 12 months',
      note:'Enter each affected driver’s age in full years and licence experience in full months, as of the pickup date. All other drivers must be at least 24 with at least 12 months of licence experience.',
      age:'Age (full years)', months:'Licence experience (full months)', add:'Add driver', remove:'Remove driver'
    } : {
      title:'יש נהג מתחת לגיל 24 או עם רישיון פחות מ־12 חודשים',
      note:'ממלאים גיל בשנים מלאות וותק רישיון בחודשים מלאים לכל נהג כזה, נכון ליום קבלת הרכב. יתר הנהגים: בני 24 ומעלה ועם רישיון לפחות 12 חודשים.',
      age:'גיל בשנים מלאות', months:'ותק רישיון בחודשים מלאים', add:'הוספת נהג', remove:'הסרת נהג'
    };
    const original = old.closest('.prc-field') || old.closest('label') || old;
    original.hidden = true;
    original.style.display = 'none';
    form.querySelectorAll('[name="driver_age"]').forEach(field => field.required=false);
    old.required = false;
    const panel = document.createElement('section'); panel.style.cssText='grid-column:1/-1;padding:12px;border:1px solid #a9c3dd;border-radius:8px';
    const label = document.createElement('label'), toggle = document.createElement('input'); toggle.type='checkbox';
    label.append(toggle,document.createTextNode(' '+text.title));
    const note=document.createElement('p'); note.textContent=text.note;
    const rows=document.createElement('div'), add=document.createElement('button'); add.type='button'; add.textContent=text.add;
    const payload=document.createElement('input'); payload.type='hidden'; payload.name='driver_requirements';
    function sync() {
      payload.value=JSON.stringify({exception:toggle.checked,drivers:toggle.checked?Array.from(rows.children).map(row=>({age:Number(row.querySelector('[data-age]').value),license_months:Number(row.querySelector('[data-months]').value)})):[]});
      if(old.type==='radio')form.querySelectorAll('[name="driver_age"]').forEach(field=>field.checked=field.value===(toggle.checked?'לא':'כן'));
      else old.value=toggle.checked?'לא':'כן';
      rows.hidden=add.hidden=!toggle.checked;
      rows.style.display=add.style.display=toggle.checked?'':'none';
      rows.querySelectorAll('input').forEach(field=>field.required=toggle.checked);
    }
    function row(values={}) {
      const box=document.createElement('div');box.style.cssText='display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0';
      for(const [key,caption,min,max] of [['age',text.age,16,100],['months',text.months,0,1019]]){
        const wrap=document.createElement('label'),input=document.createElement('input');wrap.textContent=caption;
        input.type='number';input.min=min;input.max=max;input.step=1;input.required=true;input.dataset[key]='';input.style.maxWidth='150px';
        input.value=values[key==='age'?'age':'license_months']??'';
        input.addEventListener('input',sync);wrap.append(input);box.append(wrap);
      }
      const remove=document.createElement('button');remove.type='button';remove.textContent='×';remove.setAttribute('aria-label',text.remove);
      remove.addEventListener('click',()=>{box.remove();if(!rows.children.length)toggle.checked=false;sync();});box.append(remove);rows.append(box);
    }
    toggle.addEventListener('change',()=>{if(toggle.checked&&!rows.children.length)row();sync();});
    add.addEventListener('click',()=>{if(rows.children.length<9){row();sync();}});
    const previous=form.querySelector('[name="notes"]')?.value.match(/^Driver requirements JSON:\s*(.+)$/m);
    if(previous){try{const data=JSON.parse(previous[1]);toggle.checked=data.exception===true;(data.drivers||[]).forEach(row);form.querySelector('[name="notes"]').value=form.querySelector('[name="notes"]').value.replace(/^Driver requirements JSON:.*$/m,'').trim();}catch(_){}}
    panel.append(label,note,rows,add,payload);original.after(panel);sync();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();
})();
