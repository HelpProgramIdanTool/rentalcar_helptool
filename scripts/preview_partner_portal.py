"""Render a browser-local walkthrough from the real portal templates, with invented data."""
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import shutil
from types import SimpleNamespace as NS

os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import django
django.setup()
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.template.loader import render_to_string
from partners.forms import TripForm, RecipientForm
from suppliers.models import VehicleModel, VehicleGroup

DEST=Path('output/partner-portal-preview')
DEST.mkdir(parents=True,exist_ok=True)
seed=json.loads(Path('partners/initial_content.json').read_text(encoding='utf-8'))
summaries=[NS(**row) for row in seed['summaries']]
pk='11111111-1111-4111-8111-111111111111'
partner=NS(display_name='שותף לדוגמה',email='partner@example.invalid')
trip=dict(pickup_city='Warszawa',return_city='Kraków',pickup_date='2026-12-01',return_date='2026-12-04')
draft=NS(pk=pk,trip=trip,quote=None,selected_groups=[],manual_requested=False,delivery_html='',created_at=datetime(2026,11,14,tzinfo=timezone.utc))
base=dict(copy=seed['content'],summaries=summaries,partner=partner,drafts=[],csrf_token='DEMO-NOT-A-REAL-TOKEN')
route_map={'/partners/':'index.html','/partners/login/':'login.html','/partners/logout/':'login.html','/partners/trip/':'trip.html','/partners/manual/':'manual.html',f'/partners/{pk}/options/':'options.html',f'/partners/{pk}/review/':'review.html',f'/partners/{pk}/preview/':'offer.html',f'/partners/{pk}/send/':'ready.html'}
banner='''<div class="demo-banner" dir="rtl">תצוגת הדגמה בלבד · מחירים מומצאים להמחשה · אין שליחת דוא״ל או שמירת נתונים · אין להזין סיסמה אמיתית <a href="index.html">השוואת חברות</a> · <a href="login.html">מסך כניסה</a> · <a href="trip.html">התחלת התהליך</a></div>'''
demo_css='''<style>.demo-banner{padding:12px 20px;background:#fff3d5;color:#694914;text-align:center;font:14px/1.6 Arial;border-bottom:1px solid #e7d39c}.demo-banner a{color:#694914;font-weight:bold}.demo-notice{padding:18px;background:#eaf7ef;color:#1b6239;border:1px solid #a3c8ad;margin:20px 0;border-radius:8px}</style>'''
demo_js='''<script>
document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',e=>{
 e.preventDefault();
 const file=location.pathname.split('/').pop();
 const action=e.submitter?.getAttribute('formaction')||form.getAttribute('action')||'';
 if(action==='manual.html'){location.href='manual.html';return;}
 if(file==='login.html'){location.href='index.html';return;}
 if(file==='trip.html'){
  if(!['driver_ok','credit_ok','border_ok'].every(n=>form.elements[n].checked)){location.href='manual.html';return;}
  location.href='options.html';return;
 }
 if(file==='options.html'){const ids=[...new Set([...form.querySelectorAll('[name=groups]:checked')].map(e=>e.value))];if(!ids.length)return;sessionStorage.setItem('hipl-demo-choices',JSON.stringify(ids));location.href='review.html';return;}
 if(file==='review.html'){location.href='ready.html';return;}
 const note=document.createElement('div');note.className='demo-notice';note.role='status';note.textContent='זו הדגמה בלבד — לא נשלח דוא״ל ולא נוצרה הזמנה.';form.replaceWith(note);
}));
</script>'''

def save(name,template,**kwargs):
    html=render_to_string(template,{**base,**kwargs})
    for old,new in route_map.items():
        html=html.replace('"'+old+'"','"'+new+'"')
    html=html.replace('/static/partners/','assets/')
    html=html.replace('sandbox src="offer.html"','sandbox="allow-scripts allow-same-origin" src="offer.html"')
    html=html.replace('<body>','<body>'+banner).replace('</head>',demo_css+'</head>').replace('</body>',demo_js+'</body>')
    (DEST/name).write_text(html,encoding='utf-8')

DemoTripForm=type('DemoTripForm',(forms.Form,),deepcopy(TripForm.base_fields))
form=DemoTripForm(initial={**trip,'pickup_date':datetime(2026,12,1).date(),'return_date':datetime(2026,12,4).date(),'pickup_time':'10:00','return_time':'10:00'})
for name in ('pickup_city','return_city'):
    form.fields[name].choices=[('Warszawa','ורשה · Warszawa'),('Kraków','קרקוב · Kraków'),('Prague','פראג · Prague'),('Bratislava','ברטיסלבה · Bratislava')]
mapping_folder=Path('private_uploads/vehicle-category-mapping/20261113')
mapping_source=mapping_folder/'corrected-mappings.json'
if not mapping_source.exists():
    mapping_source=mapping_folder/'approved-mappings.json'
approved=json.loads(mapping_source.read_text(encoding='utf-8'))
model_examples={}
for model in VehicleModel.objects.filter(is_active=True).select_related('vehicle_group__supplier'):
    key=(model.vehicle_group.supplier.supplier_name,model.vehicle_group.group_code)
    names=model_examples.setdefault(key,[])
    if len(names)<4:
        names.append(str(model))
category_choices={}
group_ids={}
presentation_groups={(g.supplier.supplier_name,g.group_code):g for g in VehicleGroup.objects.filter(is_active=True,show_in_offers=True).select_related('supplier')}
active_keys=set(presentation_groups)
for row in approved['mappings']:
    key=(row['supplier'],row['group_code'])
    if key not in active_keys:
        continue
    group_id=group_ids.setdefault(key,len(group_ids)+1)
    group=NS(pk=group_id,supplier=NS(supplier_name=row['supplier']),
        customer_name_he=presentation_groups[key].customer_name_he or row['category'],group_name=row['group_name'])
    # Approved membership and group names are real; prices remain explicitly illustrative.
    price=Decimal(300+group_id*10)
    option=NS(models=', '.join(model_examples.get(key,[])),total=price,currency='PLN',deposit_amount=Decimal(1000),deposit_currency='PLN')
    category_choices.setdefault(row['category'],[]).append(dict(group=group,option=option))
categories=[dict(name=name,choices=choices) for name,choices in category_choices.items()]
assert len(categories)==14, 'Expected the fourteen owner-approved categories'
assert sum(len(category['choices']) for category in categories)==sum((row['supplier'],row['group_code']) in active_keys for row in approved['mappings'])
save('index.html','partners/home.html')
save('login.html','partners/login.html',form=AuthenticationForm())
save('trip.html','partners/trip.html',form=form)
save('options.html','partners/options.html',draft=draft,categories=categories)
draft.selected_groups=[1,6]
save('review.html','partners/review.html',draft=draft,form=RecipientForm(initial={'partner_email':'partner@example.invalid','customer_name':'לקוח לדוגמה'}))
draft.quote=NS(quote_number='DEMO-OFFER',customer='לקוח לדוגמה')
save('ready.html','partners/review.html',draft=draft,addresses=['partner@example.invalid','owner@example.invalid'],deliveries=[])
save('manual.html','partners/manual.html',draft=draft)
demo_options=[]
demo_group_ids=[]
for category in categories:
    for choice in category['choices']:
        group,option=choice['group'],choice['option']
        if group.pk in demo_group_ids:
            continue
        demo_group_ids.append(group.pk)
        demo_options.append(NS(section_heading=category['name'],supplier_name_snapshot=group.supplier.supplier_name,
            display_vehicle_class=group.customer_name_he,vehicle_models_snapshot=option.models,
            total_price_gross=option.total,currency='PLN',deposit_amount=1000,deposit_currency='PLN',
            calculation_snapshot={},display_included_items=['ביטוח מלא עם ביטול השתתפות עצמית, כולל גניבה, שמשות וגלגלים','צמיגים מותאמים לעונה'],display_excluded_items=['תוספות לפי התנאים בהצעה הסופית']))
sample_quote=NS(quote_number='DEMO-OFFER',customer='לקוח לדוגמה',pickup_datetime=datetime(2026,12,1,10,tzinfo=timezone.utc),return_datetime=datetime(2026,12,4,10,tzinfo=timezone.utc),rental_days=3)
offer=render_to_string('quotes/quote_preview.html',dict(quote=sample_quote,options=demo_options,is_email=True,is_english=False,is_ltr=False,pickup_location='ורשה · נמל תעופה',return_location='קרקוב · נמל תעופה',introduction_blocks=[NS(block_key='INTRO',title='הדגמה בלבד',content='המחירים להמחשה בלבד. זו אינה הצעת מחיר תקפה ולא נשלח דוא״ל. זמינות הרכב מחייבת אישור החברה.')]))
offer=offer.replace('</body>', '<script>const demoGroupIds='+json.dumps(demo_group_ids)+';</script>'+'''<script>
const ids=JSON.parse(sessionStorage.getItem('hipl-demo-choices')||'["1","6"]'),seen=new Set();
document.querySelectorAll('article.option').forEach((el,index)=>{const selected=ids.includes(String(demoGroupIds[index]));el.hidden=!selected;const heading=el.previousElementSibling;if(heading?.classList.contains('vehicle-section')){heading.hidden=!selected||seen.has(heading.textContent);if(selected)seen.add(heading.textContent);}});
</script></body>''')
(DEST/'offer.html').write_text(offer,encoding='utf-8')
assets=DEST/'assets'
assets.mkdir(exist_ok=True)
for source in Path('partners/static/partners').iterdir():
    shutil.copyfile(source,assets/source.name)
print('Preview:',DEST.resolve()/'index.html')
print('Approved categories:',len(categories),'memberships:',sum(len(c['choices']) for c in categories),'distinct groups:',len(group_ids))
