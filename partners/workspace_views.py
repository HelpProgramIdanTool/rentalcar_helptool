import json
from uuid import UUID
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .views import partner_only, context, configuration
from .forms import WorkspaceTripForm
from .models import PartnerAccess, PartnerWorkspaceRecord
from .workspace_services import serialise_trip, workspace_options, price_valid, versions, render_workspace_offer
from django import forms


class TestOrderForm(forms.Form):
    driver_name=forms.CharField(max_length=200)
    phone=forms.CharField(max_length=60)
    email=forms.EmailField()
    additional_driver=forms.CharField(max_length=200,required=False)
    flight=forms.CharField(max_length=100,required=False)
    invoice=forms.BooleanField(required=False)
    invoice_name=forms.CharField(max_length=200,required=False)
    invoice_tax=forms.CharField(max_length=100,required=False)
    invoice_address=forms.CharField(max_length=400,required=False)
    remarks=forms.CharField(max_length=2000,required=False)

    def __init__(self,*args,**kwargs):
        self.seat_count = kwargs.pop('seat_count', 0)
        self.driver_count = kwargs.pop('driver_count', 1)
        super().__init__(*args,**kwargs)
        labels={'driver_name':'שם הנהג באנגלית','phone':'טלפון','email':'מייל איש הקשר',
                'additional_driver':'שם נהג נוסף באנגלית — אם יש','flight':'מספר טיסה',
                'invoice':'נדרשת חשבונית עם פרטים מיוחדים','invoice_name':'שם לחיוב / חברה',
                'invoice_tax':'מספר מס / זיהוי','invoice_address':'כתובת מלאה לחיוב','remarks':'הערות'}
        for name,field in self.fields.items():
            field.label=labels[name]
            field.error_messages.update(required='נא למלא שדה זה.',invalid='נא לבדוק את הערך שהוזן.')
        for index in range(1, self.seat_count + 1):
            for key, label, field in [
                ('age', 'גיל בשנים', forms.DecimalField(min_value=0, max_value=18, decimal_places=2, required=False)),
                ('height', 'גובה בס״מ', forms.DecimalField(min_value=1, max_value=250, decimal_places=2, required=False)),
                ('weight', 'משקל בק״ג', forms.DecimalField(min_value=1, max_value=150, decimal_places=2, required=False)),
                ('type_number', 'סוג הכיסא / בוסטר', forms.CharField(max_length=100, required=False)),
            ]:
                field.label = f'כיסא {index} — {label}'
                field.error_messages['invalid'] = 'נא לבדוק את הנתון של הילד.'
                self.fields[f'child_seat_{index}_{key}'] = field
        if self.driver_count>=2:self.fields['additional_driver'].required=True
        for index in range(3,self.driver_count+1):
            self.fields[f'driver_{index}_name']=forms.CharField(max_length=200,label=f'שם נהג {index} באנגלית',error_messages={'required':'נא למלא את שם הנהג.'})

    def clean(self):
        data=super().clean()
        if data.get('invoice'):
            for key in ['invoice_name','invoice_address']:
                if not data.get(key):self.add_error(key,'יש להשלים את פרטי החשבונית.')
        data['child_seat_details'] = []
        for index in range(1, self.seat_count + 1):
            seat = {key: data.pop(f'child_seat_{index}_{key}', None)
                    for key in ('age', 'height', 'weight', 'type_number')}
            if not any(value is not None and str(value).strip() for value in seat.values()):
                self.add_error(f'child_seat_{index}_age', f'כיסא {index}: יש למלא לפחות גיל, גובה, משקל או סוג כיסא.')
            data['child_seat_details'].append({key: str(value) if value is not None else '' for key,value in seat.items()})
        return data


def record_json(record):
    status=record.status
    details=dict(record.details)
    if record.booking_id:
        status={'WAITING_CONFIRMATION':'WAITING','CONFIRMED':'CONFIRMED'}.get(record.booking.status,record.booking.status)
        details.update(booking_number=record.booking.booking_number,supplier_booking_number=record.booking.supplier_booking_number)
    return dict(id=str(record.pk),number=record.number,kind=record.kind,status=status if record.status!='SEND_FAILED' else 'SEND_FAILED',
        customer_name=record.customer_name,trip=record.trip,options=record.options,
        details=details,created_at=record.created_at.isoformat(),is_test=record.is_test,booking_status=status)


@partner_only
def workspace(request):
    # This release is explicitly a server-connected test environment.
    initial={'pickup_city':'Kraków','return_city':'Kraków','pickup_service':'AIRPORT','return_service':'AIRPORT',
             'pickup_time':'10:00','return_time':'10:00','drivers':1,'seats':0}
    return render(request,'partners/workspace.html',context(request,form=WorkspaceTripForm(initial=initial),order_form=TestOrderForm()))


@partner_only
def records(request):
    return JsonResponse({'records':[record_json(r) for r in request.partner.workspace_records.filter(is_test=request.partner.is_test).select_related('draft__quote','booking').order_by('-created_at')[:100]]})


@partner_only
@require_POST
@transaction.atomic
def workspace_action(request):
    from . import live_workspace as live
    from smtplib import SMTPException
    if len(request.body)>40000:return JsonResponse({'error':'הבקשה גדולה מדי.'},status=400)
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict):raise ValueError()
    except (ValueError,UnicodeDecodeError):return JsonResponse({'error':'נתונים לא תקינים.'},status=400)
    action=data.get('action')
    if action in ('calculate','save','manual'):
        if not isinstance(data.get('trip',{}),dict):return JsonResponse({'error':'נתוני נסיעה לא תקינים.'},status=400)
        form=WorkspaceTripForm(data.get('trip',{}))
        if action!='manual' and not form.is_valid():return JsonResponse({'errors':form.errors.get_json_data()},status=400)
        trip=serialise_trip(form.cleaned_data,request.partner) if form.is_valid() else data.get('trip',{})
        if action=='manual':
            message=str(data.get('message','')).strip()[:3000]
            if not message:return JsonResponse({'error':'נא לכתוב מה צריך לבדוק.'},status=400)
            r=PartnerWorkspaceRecord.objects.create(partner=request.partner,kind='MANUAL',status='MANUAL',
                trip=trip,details={'message':message,'mail_sent':False},created_by=request.user,is_test=request.partner.is_test)
            if not r.is_test:
                try:live.notify_owner(r)
                except (SMTPException,OSError,ValidationError):return JsonResponse({'record':record_json(r),'message':'הבקשה נשמרה אך המייל לא אושר. יש לפנות לעידן ישירות.'})
            return JsonResponse({'record':record_json(r)})
        try:options,revision=workspace_options(trip)
        except ValidationError as e:return JsonResponse({'error':e.messages[0]},status=400)
        if action=='calculate':
            from .services import automatic_allowed, available_groups
            message=''
            if not options:
                if not automatic_allowed(trip):
                    message='פרטי הנסיעה או הצהרות הנהגים דורשים בדיקה אישית של עידן. שמרו פנייה לבדיקה.'
                elif not available_groups().exists():
                    message='קבוצות הרכב טרם הוגדרו להצגה בקבינט. יש לפנות לעידן להשלמת ההגדרות.'
                else:
                    message='לא נמצא תמחור מלא לתאריכים ולמסלול שנבחרו, כולל תוספות ופיקדון. שמרו פנייה לעידן לבדיקה.'
            return JsonResponse({'options':options,'manual':not bool(options),'message':message})
        if not isinstance(data.get('selected'),list):return JsonResponse({'error':'נא לבחור אפשרויות.'},status=400)
        selected=set(map(str,data['selected']))
        chosen=[o for o in options if o['id'] in selected]
        if not chosen or {o['id'] for o in chosen}!=selected:return JsonResponse({'error':'נא לבחור אפשרויות זמינות ולחשב מחדש.'},status=400)
        r=PartnerWorkspaceRecord.objects.create(partner=request.partner,kind='QUOTE',status='QUOTED',trip=trip,
            options=chosen,price_versions=revision,customer_name=(' '.join(filter(None,[trip.get('customer_first_name'),trip.get('customer_last_name')])) or trip.get('customer_email') or trip.get('customer_phone') or '')[:200],created_by=request.user,is_test=request.partner.is_test,
            details={'partner_email':request.partner.email,'customer_email':trip.get('customer_email',''),
                     'customer_phone':trip.get('customer_phone',''),'send_customer':False,'mail_sent':False})
        try:html=render_workspace_offer(r,request.user)
        except ValidationError as error:
            r.delete()
            return JsonResponse({'error':' '.join(error.messages)},status=400)
        r.details={**r.details,'preview_html':html}
        r.save(update_fields=['details','updated_at'])
        return JsonResponse({'record':record_json(r)})
    with transaction.atomic():
        try:record_id=UUID(str(data.get('id')))
        except ValueError:return JsonResponse({'error':'מספר פנייה לא תקין.'},status=400)
        r=get_object_or_404(PartnerWorkspaceRecord.objects.select_for_update(),pk=record_id,partner=request.partner,is_test=request.partner.is_test)
        config=configuration()
        copy_email=config.workspace_copy_email if config else ''
        if action in ('simulate_send','send_offer') and r.kind=='QUOTE':
            email=forms.EmailField(required=bool(data.get('send_customer')))
            try:customer_email=email.clean(data.get('customer_email',''))
            except ValidationError:return JsonResponse({'error':'יש להזין מייל תקין ללקוח.'},status=400)
            if not r.is_test:
                if not r.draft_id:return JsonResponse({'error':'חסר מקור ההצעה. יש לפנות לעידן.'},status=409)
                # Sending is also subject to the supplier's quoted-price validity.
                if any(not price_valid(r.created_at,timezone.now(),r.price_versions.get(str(o['supplier_id'])),json.loads(json.dumps(versions(o['supplier_id'])))) for o in r.options):
                    return JsonResponse({'error':'המחירון השתנה. יש ליצור הצעה מעודכנת לפני שליחה.'},status=409)
                try:live.send_offer(r,request.user,bool(data.get('send_customer')),customer_email)
                except (SMTPException,OSError,ValidationError):return JsonResponse({'error':'השליחה לא הושלמה. אפשר לנסות שוב; נמענים שכבר קיבלו לא יקבלו עותק נוסף.'},status=502)
                return JsonResponse({'record':record_json(r),'message':'ההצעה נשלחה בהצלחה, עם עותק לעידן.'})
            r.details={**r.details,'send_customer':bool(data.get('send_customer')),'customer_email':customer_email,
                'copy_email':copy_email,'mail_sent':False,'simulated_at':timezone.now().isoformat()}
            r.save(update_fields=['details','updated_at'])
            return JsonResponse({'record':record_json(r),'message':'נשמרה הדמיית שליחה. לא נשלח מייל.'})
        if action=='order' and r.kind=='QUOTE':
            from datetime import datetime
            if datetime.fromisoformat(r.trip['pickup_datetime'])<=timezone.now():
                return JsonResponse({'error':'מועד הקבלה כבר עבר. יש ליצור הצעה חדשה.'},status=409)
            if not r.is_test and not r.draft_id:
                return JsonResponse({'error':'יש ליצור הצעה חדשה לפני הזמנה.'},status=409)
            selected=next((o for o in r.options if o['id']==str(data.get('option'))),None)
            if not selected:return JsonResponse({'error':'יש לבחור אפשרות מתוך ההצעה.'},status=400)
            existing=r.orders.filter(kind='ORDER',details__option_id=selected['id']).first()
            if existing:return JsonResponse({'record':record_json(existing),'duplicate':True,'message':'ההזמנה כבר קיימת. אין לשלוח שוב; במקרה של ספק פנו לעידן.'})
            key=str(selected['supplier_id'])
            # JSON stores tuples as lists; normalise both before comparison.
            current=json.loads(json.dumps(versions(selected['supplier_id'])))
            if not price_valid(r.created_at,timezone.now(),r.price_versions.get(key),current):
                return JsonResponse({'error':'עברו 7 ימים ומחירון החברה השתנה. יש לחשב הצעה חדשה ולאשר את המחיר.'},status=409)
            if not isinstance(data.get('details',{}),dict):return JsonResponse({'error':'נא לבדוק פרטי נהג.'},status=400)
            form=TestOrderForm(data.get('details',{}),seat_count=int(r.trip.get('seats',0)),driver_count=int(r.trip.get('drivers',1)))
            if not form.is_valid():return JsonResponse({'errors':form.errors.get_json_data()},status=400)
            existing=r.orders.filter(kind='ORDER',details__option_id=selected['id']).first()
            if existing:return JsonResponse({'record':record_json(existing),'duplicate':True})
            order=PartnerWorkspaceRecord.objects.create(partner=request.partner,parent=r,kind='ORDER',status='WAITING',
                customer_name=form.cleaned_data['driver_name'],trip=r.trip,options=[selected],
                details={**form.cleaned_data,'option_id':selected['id'],'copy_email':copy_email,'mail_sent':False},created_by=request.user,is_test=r.is_test)
            if not r.is_test:
                if not r.draft_id:return JsonResponse({'error':'יש ליצור הצעה חדשה לפני הזמנה.'},status=409)
                try:
                    with transaction.atomic():
                        order.booking=live.create_booking(r,selected,form.cleaned_data,request.user)
                        order.save(update_fields=['booking','updated_at'])
                except ValidationError as error:
                    order.delete()
                    return JsonResponse({'error':' '.join(error.messages)},status=400)
                except ObjectDoesNotExist:
                    order.delete()
                    return JsonResponse({'error':'פרטי מחיר מההצעה אינם זמינים עוד. יש לפנות לעידן לבדיקה ידנית.'},status=409)
                try:live.send_booking(order,request.user)
                except (SMTPException,OSError,ValidationError,ValueError):
                    order.status='SEND_FAILED';order.save(update_fields=['status','updated_at'])
                    return JsonResponse({'record':record_json(order),'message':'ההזמנה נשמרה בתוכנית אך השליחה לא אושרה. יש לפנות לעידן; אין להזמין שוב.'})
                return JsonResponse({'record':record_json(order),'message':'ההזמנה נשלחה לחברה עם עותק לעידן. ממתינה לאישור.'})
            return JsonResponse({'record':record_json(order),'message':'הזמנת הבדיקה נשמרה. לא נשלח מייל לחברה.'})
        if action in ('change','cancel') and r.kind=='ORDER':
            message=str(data.get('message','')).strip()[:3000]
            if not message:return JsonResponse({'error':'נא לתאר את הבקשה.'},status=400)
            note=PartnerWorkspaceRecord.objects.create(partner=request.partner,parent=r,kind='CHANGE',status='MANUAL',
                trip=r.trip,details={'action':action,'message':message,'mail_sent':False},created_by=request.user,is_test=r.is_test)
            if not note.is_test:
                try:live.notify_owner(note)
                except (SMTPException,OSError,ValidationError):return JsonResponse({'record':record_json(note),'message':'הבקשה נשמרה אך המייל לא אושר. יש לפנות לעידן ישירות.'})
            return JsonResponse({'record':record_json(note),'message':'הבקשה נשמרה לעידן. ההזמנה לא שונתה.'})
    return JsonResponse({'error':'הפעולה אינה זמינה.'},status=400)


@login_required
def owner(request):
    if not request.user.is_superuser:return HttpResponseForbidden()
    if request.method=='POST':
        partner=get_object_or_404(PartnerAccess,pk=request.POST.get('partner'),is_active=True)
        request.session['partner_preview_id']=partner.pk
        return redirect('partners:workspace')
    return render(request,'partners/workspace_owner.html',{'partners':PartnerAccess.objects.all()})
