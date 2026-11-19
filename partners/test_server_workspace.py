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

    def trip_data(self,**changes):return fixtures.PartnerFlowTests.trip_data(self,**changes)

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
        result=self.action(action='calculate',trip=self.trip_data())
        self.assertEqual(result.status_code,200)
        option=next(o for o in result.json()['options'] if o['id']==str(self.group.pk))
        self.assertEqual(option['name'],'TEST-GROUP-HE')
        self.assertEqual(Decimal(option['total']),self.rate.daily_rate_gross*3)
        saved=self.quote()
        self.assertTrue(PartnerWorkspaceRecord.objects.filter(pk=saved['id'],partner=self.partner).exists())
        rows=self.client.get(reverse('partners:workspace_records')).json()['records']
        self.assertEqual(rows[0]['customer_name'],'TEST-CUSTOMER')

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
