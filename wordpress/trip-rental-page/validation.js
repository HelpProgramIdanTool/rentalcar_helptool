/* Preview-only validation. No network calls or storage. Times follow Europe/Warsaw. */
(function(scope){
const zoneFormatter=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function wallParts(instant){const p=Object.fromEntries(zoneFormatter.formatToParts(new Date(instant)).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));return {date:`${p.year}-${p.month}-${p.day}`,time:`${p.hour}:${p.minute}`};}
function validDate(value){if(!/^\d{4}-\d{2}-\d{2}$/.test(value||''))return false;const [y,m,d]=value.split('-').map(Number);const parsed=new Date(Date.UTC(y,m-1,d));return parsed.getUTCFullYear()===y&&parsed.getUTCMonth()===m-1&&parsed.getUTCDate()===d;}
function validTime(value){return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value||'');}
function candidates(date,time){if(!validDate(date)||!validTime(time))return [];const [y,m,d]=date.split('-').map(Number),[h,min]=time.split(':').map(Number);const utc=Date.UTC(y,m-1,d,h,min),result=[];for(let offset=-180;offset<=180;offset+=30){const stamp=utc+offset*60000,p=wallParts(stamp);if(p.date===date&&p.time===time)result.push(stamp);}return result.sort((a,b)=>a-b);}
function validateTrip(d,now=Date.now()){
 const errors=[];
 if(!validDate(d.pickupDate))errors.push({field:'pickupDate',message:'בחרו תאריך קבלה תקין.'});
 if(!validDate(d.returnDate))errors.push({field:'returnDate',message:'בחרו תאריך החזרה תקין.'});
 if(!validTime(d.pickupTime))errors.push({field:'pickupTime',message:'בחרו שעת קבלה בפורמט 24 שעות.'});
 if(!validTime(d.returnTime))errors.push({field:'returnTime',message:'בחרו שעת החזרה בפורמט 24 שעות.'});
 if(errors.length)return {errors};
 const starts=candidates(d.pickupDate,d.pickupTime),ends=candidates(d.returnDate,d.returnTime);
 if(!starts.length)errors.push({field:'pickupTime',message:'שעת הקבלה אינה קיימת ביום זה בגלל המעבר לשעון קיץ. בחרו שעה אחרת.'});
 if(!ends.length)errors.push({field:'returnTime',message:'שעת ההחזרה אינה קיימת ביום זה בגלל המעבר לשעון קיץ. בחרו שעה אחרת.'});
 if(errors.length)return {errors};
 // On the repeated autumn hour, consistently use the first occurrence for both sides.
 const start=starts[0],end=ends[0];
 if(start<now)errors.push({field:'pickupDate',message:'לא ניתן לבחור מועד קבלה שכבר עבר. בדקו תאריך ושעה.'});
 if(end<=start)errors.push({field:'returnDate',message:'מועד ההחזרה חייב להיות אחרי מועד הקבלה. לאחר חצות בחרו את היום הבא.'});
 return {errors,start,end};
}
function fieldMessage(field){
 if(field.checkValidity())return '';
 const titles={name:'שם ושם משפחה',email:'כתובת דואר אלקטרוני',passengers:'מספר הנוסעים',bags:'מספר המזוודות',pickupCity:'עיר קבלה',returnCity:'עיר החזרה'};
 const title=titles[field.name]||'השדה המסומן';
 if(field.validity.valueMissing)return 'נא למלא '+title+'.';
 if(field.validity.typeMismatch)return 'נא להזין כתובת דואר אלקטרוני תקינה.';
 if(field.validity.rangeUnderflow||field.validity.rangeOverflow)return title+': יש לבחור מספר בין '+field.min+' ל-'+(field.max||'הערך המרבי')+'.';
 if(field.validity.badInput||field.validity.stepMismatch)return title+': נא להזין מספר שלם ותקין.';
 return 'נא לבדוק את '+title+'.';
}
const api={wallParts,validDate,validTime,candidates,validateTrip,fieldMessage};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else scope.TripValidation=api;
})(typeof globalThis!=='undefined'?globalThis:this);
