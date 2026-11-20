import io
import json
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, SimpleTestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from . import tests as fixtures
from .models import PartnerWorkspaceRecord
from .workspace_services import price_valid


class PriceValidityTests(SimpleTestCase):
    def test_each_child_seat_requires_one_parameter_and_accepts_any_of_four(self):
        from .workspace_views import TestOrderForm
        base={'driver_name':'TEST DRIVER','phone':'0000','email':'test@example.invalid'}
        for key,value in [('age','0'),('height','95'),('weight','15'),('type_number','TEST TYPE')]:
            form=TestOrderForm({**base,'child_seat_1_'+key:value},seat_count=1)
            self.assertTrue(form.is_valid(),form.errors)
            self.assertEqual(form.cleaned_data['child_seat_details'][0][key],value)
        form=TestOrderForm({**base,'child_seat_1_age':'4'},seat_count=2)
        self.assertFalse(form.is_valid())
        self.assertIn('child_seat_2_age',form.errors)
        form=TestOrderForm({**base,'child_seat_1_age':'-1','child_seat_1_type_number':'TEST TYPE'},seat_count=1)
        self.assertFalse(form.is_valid())
        form=TestOrderForm({**base,'child_seat_1_type_number':'   '},seat_count=1)
        self.assertFalse(form.is_valid())

    def test_first_week_protects_old_price_and_later_requires_matching_supplier_versions(self):
        start=timezone.now()
        self.assertTrue(price_valid(start,start+timedelta(days=6),[1],[2]))
        self.assertFalse(price_valid(start,start+timedelta(days=8),[1],[2]))
        self.assertTrue(price_valid(start,start+timedelta(days=8),[1],[1]))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ServerWorkspaceTests(TestCase):
    def setUp(self):
        fixtures.PartnerFlowTests.setUp(self)
        self.group.deposit_amount=Decimal('50.00')
        self.group.save(update_fields=['deposit_amount'])
        for partner in [self.partner,self.other]:
            partner.is_test=True;partner.save(update_fields=['is_test'])

    def trip_data(self,**changes):return fixtures.PartnerFlowTests.trip_data(self,**{'customer_first_name':'TEST-CUSTOMER',**changes})

    def action(self,**payload):
        return self.client.post(reverse('partners:workspace_action'),json.dumps(payload),content_type='application/json')

    def quote(self):
        result=self.action(action='save',trip=self.trip_data(),selected=[str(self.group.pk)],customer_name='TEST-CUSTOMER')
        self.assertEqual(result.status_code,200,result.content)
        return result.json()['record']

    def test_page_calculation_and_saved_quote_use_live_database_and_survive_new_request(self):
        page=self.client.get(reverse('partners:workspace'))
        self.assertContains(page,'לתת הצעה')
        self.assertContains(page,'data-date-target')
        self.assertContains(page,'id="copy-offer"')
        self.assertContains(page,'id="copy-fallback"')
        self.assertContains(page,'id="send-form"')
        self.assertContains(page,'id="offer-preview"')
        html=page.content.decode()
        self.assertLess(html.index('id="offer-preview"'),html.index('id="send-offer"'))
        self.assertLess(html.index('id="send-offer"'),html.index('id="saved-options"'))
        self.assertLess(html.index('id="copy-offer"'),html.index('id="saved-options"'))
        self.assertContains(page,'form="send-form"')
        self.assertNotContains(page,'name="gps"')
        self.assertNotContains(page,'name="countries"')
        result=self.action(action='calculate',trip=self.trip_data())
        self.assertEqual(result.status_code,200)
        option=next(o for o in result.json()['options'] if o['id']==str(self.group.pk))
        self.assertEqual(option['name'],'TEST-GROUP-HE')
        self.assertEqual(Decimal(option['total']),self.rate.daily_rate_gross*3)
        saved=self.quote()
        self.assertTrue(PartnerWorkspaceRecord.objects.filter(pk=saved['id'],partner=self.partner).exists())
        rows=self.client.get(reverse('partners:workspace_records')).json()['records']
        self.assertEqual(rows[0]['customer_name'],'TEST-CUSTOMER')
        self.assertIn('TEST-GROUP-HE',saved['details']['preview_html'])
        self.assertIn(saved['number'],saved['details']['preview_html'])
        from quotes.models import Quote
        from customers.models import Customer
        from .models import PartnerDraft
        self.assertFalse(Quote.objects.exists())
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(PartnerDraft.objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_workspace_ignores_gps_and_does_not_require_destination_countries(self):
        from .forms import WorkspaceTripForm
        form=WorkspaceTripForm(self.trip_data(cross_border=True,gps=True,countries='IGNORED'))
        self.assertTrue(form.is_valid(),form.errors)
        self.assertTrue(form.cleaned_data['cross_border'])
        self.assertFalse(form.cleaned_data['gps'])
        self.assertEqual(form.cleaned_data['countries'],'')
        form=WorkspaceTripForm(self.trip_data(cross_border=True))
        self.assertTrue(form.is_valid(),form.errors)

    def test_customer_requires_one_valid_contact_detail_and_preserves_it(self):
        from .forms import WorkspaceTripForm
        empty=dict(customer_first_name='',customer_last_name='',customer_email='',customer_phone='')
        response=self.action(action='calculate',trip=self.trip_data(**empty))
        self.assertEqual(response.status_code,400)
        self.assertIn('customer_first_name',response.json()['errors'])
        for key,value in [('customer_first_name','TEST FIRST'),('customer_last_name','TEST LAST'),
                          ('customer_email','test@example.invalid'),('customer_phone','000123')]:
            form=WorkspaceTripForm(self.trip_data(**{**empty,key:value}))
            self.assertTrue(form.is_valid(),form.errors)
        form=WorkspaceTripForm(self.trip_data(customer_email='broken-email'))
        self.assertFalse(form.is_valid())
        response=self.action(action='save',trip=self.trip_data(**{**empty,'customer_phone':'000123'}),selected=[str(self.group.pk)])
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['record']['trip']['customer_phone'],'000123')
        self.assertEqual(response.json()['record']['customer_name'],'000123')

    def test_invalid_trip_dates_are_rejected_without_saving_or_calculating(self):
        from unittest.mock import patch
        yesterday=(timezone.localdate()-timedelta(days=1)).strftime('%d.%m.%Y')
        cases=[({'pickup_date':yesterday},'pickup_date'),
               ({'pickup_date':'31.02.2027'},'pickup_date'),
               ({'return_date':'01.01.2020'},'return_date')]
        with patch('partners.workspace_views.workspace_options') as calculate:
            for changes,field in cases:
                for action in ['calculate','save']:
                    response=self.action(action=action,trip=self.trip_data(**changes),selected=[str(self.group.pk)])
                    self.assertEqual(response.status_code,400,response.content)
                    self.assertIn(field,response.json()['errors'])
            calculate.assert_not_called()
        self.assertFalse(PartnerWorkspaceRecord.objects.exists())

    def test_empty_results_explain_missing_configuration_or_manual_route(self):
        self.group.form_categories.clear()
        result=self.action(action='calculate',trip=self.trip_data())
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['options'],[])
        self.assertTrue(result.json()['message'])
        missing_configuration=result.json()['message']
        result=self.action(action='calculate',trip=self.trip_data(driver_ok=False))
        self.assertEqual(result.json()['options'],[])
        self.assertTrue(result.json()['message'])
        self.assertNotEqual(result.json()['message'],missing_configuration)

    def test_test_order_is_idempotent_saved_with_invoice_and_never_sent(self):
        quote=self.quote()
        payload=dict(action='order',id=quote['id'],option=str(self.group.pk),details={
            'driver_name':'TEST DRIVER','phone':'000000','email':'driver@example.invalid','invoice':True,
            'invoice_name':'TEST COMPANY','invoice_address':'TEST ADDRESS','additional_driver':'TEST DRIVER TWO'})
        first=self.action(**payload)
        self.assertEqual(first.status_code,200,first.content)
        second=self.action(**payload)
        self.assertEqual(first.json()['record']['id'],second.json()['record']['id'])
        self.assertEqual(PartnerWorkspaceRecord.objects.filter(kind='ORDER').count(),1)
        self.assertEqual(first.json()['record']['details']['invoice_name'],'TEST COMPANY')
        self.assertEqual(first.json()['record']['status'],'WAITING')
        from bookings.models import Booking
        self.assertEqual(Booking.all_objects.count(),0)
        self.assertEqual(len(mail.outbox),0)

    def test_child_seat_count_comes_from_saved_quote_and_details_are_preserved(self):
        quote=self.quote()
        record=PartnerWorkspaceRecord.objects.get(pk=quote['id'])
        record.trip={**record.trip,'seats':2}
        record.save(update_fields=['trip'])
        details={'driver_name':'TEST DRIVER','phone':'0000','email':'test@example.invalid','child_seat_1_age':'3'}
        payload=dict(action='order',id=quote['id'],option=str(self.group.pk),details=details)
        response=self.action(**payload)
        self.assertEqual(response.status_code,400)
        self.assertIn('child_seat_2_age',response.json()['errors'])
        self.assertFalse(PartnerWorkspaceRecord.objects.filter(kind='ORDER').exists())
        details['child_seat_2_type_number']='TEST BOOSTER'
        details['child_seat_1_weight']='14'
        response=self.action(**payload)
        self.assertEqual(response.status_code,200,response.content)
        seats=response.json()['record']['details']['child_seat_details']
        self.assertEqual(len(seats),2)
        self.assertEqual(seats[0]['weight'],'14')
        self.assertEqual(seats[1]['type_number'],'TEST BOOSTER')
        self.assertEqual(len(mail.outbox),0)
        self.assertEqual(self.action(action='simulate_send',id=quote['id'],send_customer=True,customer_email='client@example.invalid').status_code,200)
        self.assertEqual(len(mail.outbox),0)

    def test_other_partner_records_cannot_be_read_or_ordered(self):
        quote=self.quote()
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse('partners:workspace_records')).json()['records'],[])
        response=self.action(action='order',id=quote['id'],option=str(self.group.pk),details={})
        self.assertEqual(response.status_code,404)

    def test_existing_mail_routes_are_blocked_for_test_user(self):
        from .models import PartnerDraft
        draft=PartnerDraft.objects.create(partner=self.partner)
        for name in ['send','review','options']:
            self.assertEqual(self.client.post(reverse('partners:'+name,args=[draft.pk]),{}).status_code,403)
        self.assertEqual(self.client.post(reverse('partners:manual'),{'message':'TEST'}).status_code,403)
        self.assertEqual(len(mail.outbox),0)

    def test_change_request_does_not_modify_test_order(self):
        quote=self.quote()
        order=self.action(action='order',id=quote['id'],option=str(self.group.pk),details={
            'driver_name':'TEST DRIVER','phone':'0000','email':'driver@example.invalid'}).json()['record']
        result=self.action(action='cancel',id=order['id'],message='TEST CANCEL')
        self.assertEqual(result.status_code,200)
        self.assertEqual(PartnerWorkspaceRecord.objects.get(pk=order['id']).status,'WAITING')
        self.assertEqual(len(mail.outbox),0)

    def test_owner_can_open_test_cabinet_without_changing_owner_credentials(self):
        self.assertEqual(self.client.get(reverse('partners:workspace_owner')).status_code,403)
        owner=get_user_model().objects.create_superuser(username='TEST-OWNER',email='owner@example.invalid',password='TEST-PASS')
        self.client.force_login(owner)
        self.assertRedirects(self.client.get(reverse('partners:workspace')),reverse('partners:workspace_owner'))
        self.assertEqual(self.client.post(reverse('partners:workspace_action'),{},content_type='application/json').status_code,403)
        session=self.client.session
        session['partner_preview_id']=999999999
        session.save()
        self.assertRedirects(self.client.get(reverse('partners:workspace')),reverse('partners:workspace_owner'))
        response=self.client.post(reverse('partners:workspace_owner'),{'partner':self.partner.pk})
        self.assertRedirects(response,reverse('partners:workspace'))
        self.assertEqual(self.client.session['_auth_user_id'],str(owner.pk))
        self.assertContains(self.client.get(reverse('partners:workspace')),self.partner.display_name)

    def test_account_command_creates_restricted_account_with_generated_password(self):
        output=io.StringIO()
        call_command('create_partner_test',username='NEW-TEST-ACCOUNT',email='owner@example.invalid',stdout=output)
        text=output.getvalue();password=text.split('PASSWORD: ')[1].splitlines()[0]
        user=get_user_model().objects.get(username='NEW-TEST-ACCOUNT')
        self.assertTrue(user.check_password(password));self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser)
        self.assertTrue(user.partner_access.is_test)
        self.assertTrue(user.partner_access.is_active)
        output=io.StringIO();call_command('create_partner_test',username='NEW-TEST-ACCOUNT',email='owner@example.invalid',stdout=output)
        self.assertNotIn('PASSWORD:',output.getvalue())

    def test_csrf_is_required_and_inactive_city_is_not_reintroduced_by_fallback(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        client.get(reverse('partners:workspace'))
        payload=json.dumps({'action':'calculate','trip':self.trip_data()})
        url=reverse('partners:workspace_action')
        self.assertEqual(client.post(url,payload,content_type='application/json').status_code,403)
        self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)
        from suppliers.models import OfferCity
        from .forms import TripForm
        OfferCity.objects.update_or_create(name='Warszawa',defaults={'label':'TEST-LABEL','country':'Poland','is_active':False})
        choices=dict(TripForm().fields['pickup_city'].choices)
        self.assertNotIn('Warszawa',choices)
        self.assertEqual(choices['TEST-CITY'],'TEST-CITY-HE')
