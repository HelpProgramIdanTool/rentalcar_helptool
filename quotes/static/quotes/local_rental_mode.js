(function () {
  'use strict';
  var select=document.getElementById('id_local_rental_branch');
  var data=document.getElementById('local-rental-modes');
  if(!select||!data)return;
  var modes=JSON.parse(data.textContent),form=select.form;
  var country=document.getElementById('id_rental_country');
  var border=document.getElementById('id_cross_border_requested');
  var borderLabel=border.closest('label'),normalBorder=borderLabel.lastChild.textContent;
  var help=document.getElementById('local-mode-help');
  var wasLocal=false;
  function sync(changed){
    var mode=modes[select.value];
    var clearLocal=!mode&&wasLocal;
    wasLocal=!!mode;
    if(changed)country.value=mode?mode.country:'PL';
    country.disabled=!!mode;
    country.setAttribute('aria-readonly',mode?'true':'false');
    if(mode)country.value=mode.country;
    if(borderLabel.lastChild.nodeType===3)borderLabel.lastChild.textContent=mode?' '+mode.cross_border_label:normalBorder;
    help.textContent=mode?mode.help:'';
    document.getElementById('ordinary-rental-mode').hidden=!mode;
    if(!mode&&!changed&&!clearLocal)return;
    form.querySelectorAll('input[name="suppliers"]').forEach(function(input){
      var other=mode&&input.value!==mode.supplier;
      var unavailable=input.closest('label').dataset.availabilityHidden==='1';
      input.disabled=!!other||unavailable;input.closest('label').hidden=!!other||unavailable;
      if(mode)input.checked=!other;
    });
    form.querySelectorAll('.vehicle-picker input[type="checkbox"]').forEach(function(input){
      var other=mode&&input.dataset.supplierId!==mode.supplier;
      var unavailable=input.closest('label').dataset.availabilityHidden==='1';
      input.disabled=!!other||unavailable;input.closest('label').hidden=!!other||unavailable;
      if(other)input.checked=false;
    });
    form.querySelectorAll('.vehicle-supplier, .vehicle-section').forEach(function(box){
      var inputs=Array.from(box.querySelectorAll('input[type="checkbox"]'));
      if(inputs.length)box.hidden=inputs.every(function(input){return input.disabled;});
    });
    ['pickup','return'].forEach(function(side){
      var city=document.getElementById('id_'+side+'_city');
      Array.from(city.options).forEach(function(option){
        var hide=mode&&option.value&&mode.cities.indexOf(option.value)===-1;
        option.hidden=!!hide;option.disabled=!!hide;
      });
      if(changed&&mode&&mode.cities.indexOf(city.value)===-1)city.value=mode.city;
    });
  }
  form.addEventListener('change',function(event){sync(event.target===select);},true);
  form.addEventListener('pricingrendered',function(){sync(false);});
  document.getElementById('ordinary-rental-mode').addEventListener('click',function(){
    select.value='';select.dispatchEvent(new Event('change',{bubbles:true}));
    document.getElementById('id_pickup_city').dispatchEvent(new Event('change',{bubbles:true}));
  });
  var restore=document.getElementById('restore-draft');
  if(restore)restore.addEventListener('click',function(){setTimeout(function(){sync(false);},0);});
  var showAll=document.getElementById('show-all-groups');
  if(showAll)showAll.addEventListener('click',function(){sync(false);});
  sync(false);
}());
