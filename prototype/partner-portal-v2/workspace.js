'use strict';
// Presentation only. No network, persistence, authentication or actual pricing.
const OWNER='idan.caliber@gmail.com';
const state={owner:false,partner:1,selected:new Set(['one-suv','mm-suv']),recipient:'partner',tour:-1,booked:false,manual:false,request:false,expired:false,filter:'all',trip:{pickup:'קרקוב · שדה תעופה',dropoff:'קרקוב · שדה תעופה',from:'01.12.2026',to:'05.12.2026',time:'10:00',returnTime:'10:00'},driver:'',invoice:''};
const names={1:'שותף לדוגמה',2:'שותף נוסף לדוגמה'};
const choices=[
 {id:'one-suv',company:'One Rent',group:'SUV Premium medium AT',models:'Volvo XC60, Lexus NX, Audi Q5 או דומה',categories:[10]},
 {id:'mm-suv',company:'MM Cars',group:'PREMIUM SUV',models:'Volvo XC60 או דומה',categories:[10]},
 {id:'carfree-d',company:'CarFree',group:'D Automatic',models:'הדגמים יוצגו מהקבוצה שבמחירון',categories:[3]},
 {id:'kaizen-f',company:'Kaizen Rent',group:'SUV Aut big · FFAR',models:'הדגמים יוצגו מהקבוצה שבמחירון',categories:[7,6]}
];
const categories=['רכב קטן','רכב סטנדרטי סדאן','רכב סטיישן','רכב משפחתי / מנהלים גדול, סדאן','רכב היברידי','קראסאובר SUV קטן','קראסאובר SUV בינוני','קראסאובר SUV גדול','רכב פרמיום סדאן','רכב פרמיום SUV קטן','רכב פרמיום SUV בינוני','רכב פרמיום SUV גדול','רכב של 7 מקומות','רכב 8/9 מקומות'];
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge=(text,color='')=>`<span class="status ${color}">${text}</span>`;
const button=(text,route,primary=false)=>`<a class="button ${primary?'primary':''}" href="#${route}">${text}</a>`;
const steps=n=>`<ol class="steps">${['פרטי הנסיעה','בחירת רכבים','שליחת ההצעה','הזמנה ומעקב'].map((s,i)=>`<li class="${i===n?'active':''}">${i+1} · ${s}</li>`).join('')}</ol>`;
const heading=(eyebrow,title,subtitle,action='')=>`<div class="page-top"><div><span class="eyebrow">${eyebrow}</span><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
const field=(label,name,value='',type='text',required=false)=>`<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${required?'required':''}></label>`;
function toast(text){$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>$('#toast').hidden=true,4500);}
function comparison(){return `<details class="company-compare"><summary>איזו חברה מתאימה ללקוח? השוואה קצרה</summary><div class="table-wrap"><table><thead><tr><th>מה חשוב לדעת</th><th>One Rent</th><th>CarFree</th><th>MM Cars</th><th>Kaizen Rent</th></tr></thead><tbody><tr><td>רכבים עד שנתיים</td><td>כן</td><td>כן</td><td>כן</td><td>לפי ההצעה</td></tr><tr><td>דלפקים ברוב שדות התעופה</td><td>יש לבדוק</td><td>כן</td><td>יש לבדוק</td><td>כן</td></tr><tr><td>קבלה בטרמינל</td><td>כן</td><td>כן</td><td>כן</td><td>כן</td></tr><tr><td>החזרה בטרמינל</td><td>תלוי בשדה</td><td>תמיד</td><td>תלוי בשדה</td><td>תמיד</td></tr><tr><td>מדיניות דלק</td><td>מלא למלא</td><td>כמו שקיבלתם</td><td>מלא למלא</td><td>מלא למלא</td></tr><tr><td>GPS להזמנה</td><td>לא</td><td>כן</td><td>כן</td><td>כן</td></tr></tbody></table></div><p class="hint green">בכל החברות: ביטוח מלא עם ביטול השתתפות עצמית, כולל גניבה, שמשות וגלגלים, בכפוף לתנאי ההשכרה; צמיגים לעונה ואפשרות להזמין שרשראות.</p></details>`;}
