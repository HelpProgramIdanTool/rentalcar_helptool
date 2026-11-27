(function(){
  function sync(root){
    root.querySelectorAll('[data-booking-driver]').forEach(box=>{
      const checked=box.querySelector('[data-booking-exception]')?.checked===true;
      const details=box.querySelector('[data-driver-extra]');if(!details)return;
      details.hidden=!checked;
      details.querySelectorAll('input').forEach(field=>{field.disabled=!checked;field.required=checked;});
    });
  }
  document.addEventListener('change',event=>{if(event.target.matches('[data-booking-exception]'))sync(document);});
  document.addEventListener('bookingdriversloaded',()=>sync(document));
  sync(document);
})();
