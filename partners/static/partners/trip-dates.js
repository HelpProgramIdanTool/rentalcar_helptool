'use strict';
// Date-only comparisons do not depend on the browser's time zone.
(()=>{
 function parse(value){
  const match=/^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value||'');
  if(!match)return null;
  const date=new Date(Date.UTC(+match[3],+match[2]-1,+match[1]));
  return date.getUTCFullYear()===+match[3]&&date.getUTCMonth()===+match[2]-1&&date.getUTCDate()===+match[1]?date.getTime():null;
 }
 function minimum(today,pickup,pickupTime,isReturn){
  let result=parse(today);
  const start=parse(pickup);
  if(isReturn&&start!==null){
   const earliest=start+(pickupTime==='23:30'?86400000:0);
   result=Math.max(result,earliest);
  }
  return result;
 }
 function reversed(pickup,pickupTime,returned,returnTime){
  const start=parse(pickup),end=parse(returned);
  return start!==null&&end!==null&&(end<start||(end===start&&!!pickupTime&&!!returnTime&&returnTime<=pickupTime));
 }
 const api={parse,minimum,reversed};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else window.PartnerTripDates=api;
})();
