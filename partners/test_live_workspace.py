import io
import json
from decimal import Decimal
from unittest.mock import patch
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from . import test_server_workspace as server_fixtures
from .models import PartnerAccess, PartnerWorkspaceRecord, PortalConfiguration

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LiveWorkspaceTests(TestCase):
    def setUp(self):
        server_fixtures.ServerWorkspaceTests.setUp(self)
        self.partner.is_test=False;self.partner.save(update_fields=['is_test'])
        config=PortalConfiguration.objects.first();config.workspace_copy_email='owner@example.invalid';config.save()
        self.supplier.booking_email='supplier@example.invalid';self.supplier.save(update_fields=['booking_email'])
    trip_data=server_fixtures.ServerWorkspaceTests.trip_data
    action=server_fixtures.ServerWorkspaceTests.action
    quote=server_fixtures.ServerWorkspaceTests.quote

    def order(self,quote):
        return self.action(action='order',id=quote['id'],option=str(self.group.pk),details={
            'driver_name':'TEST DRIVER','phone':'0000','email':'driver@example.invalid'})

    def test_live_quote_persists_and_sends_only_on_explicit_action_with_owner_copy(self):
        quote=self.quote()
        record=PartnerWorkspaceRecord.objects.get(pk=quote['id'])
        self.assertFalse(record.is_test)
        self.assertIsNotNone(record.draft.quote_id)
        self.assertFalse(record.number.startswith('TEST-'))
        self.assertEqual(len(mail.outbox),0)
        response=self.action(action='send_offer',id=quote['id'],send_customer=True,customer_email='customer@example.invalid')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(len(mail.outbox),2)
        self.assertEqual({m.to[0] for m in mail.outbox},{self.partner.email,'customer@example.invalid'})
        for message in mail.outbox:
            self.assertEqual(message.bcc,['owner@example.invalid'])
            self.assertIn('[PARTNER',message.subject)
        self.action(action='send_offer',id=quote['id'],send_customer=True,customer_email='customer@example.invalid')
        self.assertEqual(len(mail.outbox),2)

    def test_live_order_uses_native_booking_frozen_price_and_does_not_duplicate(self):
        quote=self.quote()
        quoted=Decimal(quote['options'][0]['total'])
        self.rate.daily_rate_gross+=Decimal('100');self.rate.save()
        response=self.order(quote)
        self.assertEqual(response.status_code,200,response.content)
        order=response.json()['record']
        record=PartnerWorkspaceRecord.objects.get(pk=order['id'])
        self.assertIsNotNone(record.booking_id)
        self.assertEqual(record.booking.total_price_gross,quoted)
        self.assertEqual(record.booking.status,'WAITING_CONFIRMATION')
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['supplier@example.invalid'])
        self.assertEqual(mail.outbox[0].bcc,['owner@example.invalid'])
        self.assertIn('TEST DRIVER',mail.outbox[0].body)
        self.order(quote)
        self.assertEqual(len(mail.outbox),1)
        from bookings.models import Booking
        self.assertEqual(Booking.all_objects.count(),1)
        record.booking.status='CONFIRMED';record.booking.supplier_booking_number='TEST-RES-001';record.booking.save(update_fields=['status','supplier_booking_number'])
        rows=self.client.get(reverse('partners:workspace_records')).json()['records']
        saved=next(row for row in rows if row['kind']=='ORDER')
        self.assertEqual(saved['status'],'CONFIRMED')
        self.assertEqual(saved['details']['supplier_booking_number'],'TEST-RES-001')

    def test_send_failure_keeps_one_native_order_and_does_not_claim_sent(self):
        quote=self.quote()
        with patch('partners.live_workspace.EmailMultiAlternatives.send',side_effect=OSError('TEST ERROR')):
            response=self.order(quote)
        self.assertEqual(response.status_code,200,response.content)
        record=PartnerWorkspaceRecord.objects.get(pk=response.json()['record']['id'])
        self.assertEqual(record.status,'SEND_FAILED')
        self.assertFalse(record.details['mail_sent'])
        self.assertEqual(record.booking.status,'DRAFT')
        self.assertEqual(record.booking.supplier_deliveries.get().status,'FAILED')
        self.order(quote)
        self.assertEqual(len(mail.outbox),0)

    def test_protected_extra_price_survives_a_supplier_rate_change(self):
        from suppliers.models import SupplierExtra,SupplierExtraRate
        extra=SupplierExtra.objects.create(supplier=self.supplier,extra_code='TEST_FIXED',name='TEST SERVICE',is_mandatory=True)
        rate=SupplierExtraRate.objects.create(extra=extra,calculation_type='PER_RENTAL',amount_gross=Decimal('20'),valid_from=self.pickup.date())
        quote=self.quote()
        quoted=Decimal(quote['options'][0]['total'])
        rate.amount_gross=Decimal('200');rate.currency='EUR';rate.save()
        response=self.order(quote)
        self.assertEqual(response.status_code,200,response.content)
        record=PartnerWorkspaceRecord.objects.get(pk=response.json()['record']['id'])
        self.assertEqual(record.booking.total_price_gross,quoted)
        saved=record.booking.extras.get(extra=extra)
        self.assertEqual(saved.calculated_price_gross,Decimal('20'))
        self.assertEqual(saved.unit_price_gross_snapshot,Decimal('20'))
        self.assertEqual(saved.currency_snapshot,'PLN')

    def test_changes_go_to_owner_and_other_partners_cannot_read_or_send(self):
        quote=self.quote();order=self.order(quote).json()['record']
        response=self.action(action='cancel',id=order['id'],message='TEST CANCEL')
        self.assertEqual(response.status_code,200)
        self.assertEqual(mail.outbox[-1].to,['owner@example.invalid'])
        record=PartnerWorkspaceRecord.objects.get(pk=order['id'])
        self.assertEqual(record.booking.status,'WAITING_CONFIRMATION')
        self.client.force_login(self.other_user)
        self.assertEqual(self.action(action='send_offer',id=quote['id']).status_code,404)
        self.assertEqual(self.client.get(reverse('partners:workspace_records')).json()['records'],[])

    def test_create_command_creates_normal_partner_without_email_or_global_privileges(self):
        output=io.StringIO()
        call_command('create_partner',email='new@example.invalid',name='TEST PARTNER',owner_copy='owner@example.invalid',stdout=output)
        partner=PartnerAccess.objects.get(email='new@example.invalid')
        password=output.getvalue().split('PASSWORD: ')[1].splitlines()[0]
        self.assertTrue(partner.user.check_password(password))
        self.assertFalse(partner.is_test);self.assertFalse(partner.user.is_staff);self.assertFalse(partner.user.is_superuser)
        output=io.StringIO();call_command('create_partner',email='new@example.invalid',name='TEST PARTNER',stdout=output)
        self.assertNotIn('PASSWORD:',output.getvalue())
        self.assertEqual(len(mail.outbox),0)
